"""
RFC synchronization and processing pipeline.

This module handles downloading RFC documents from the official mirror,
sectionizing them, and building searchable indexes with content-addressed storage.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import httpx
import orjson
from lxml import etree
from tenacity import retry, stop_after_attempt, wait_exponential

from ..contracts.models import RFCSection
from ..contracts.settings import settings

logger = logging.getLogger(__name__)


class RFCSyncError(Exception):
    """Exception raised during RFC synchronization."""

    pass


class RFCSectionizer:
    """Handles sectionization of RFC documents."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.sectionizer")

    def sectionize_xml(self, xml_content: str, rfc_number: int) -> List[RFCSection]:
        """Sectionize an RFC XML document."""
        try:
            root = etree.fromstring(xml_content.encode("utf-8"))
            sections = []

            # Extract RFC title (unused but kept for potential future use)
            # title_elem = root.find('.//rfc/front/title')

            # Process sections
            for section in root.findall(".//rfc/middle/section"):
                section_id = section.get("anchor", "")
                section_number = section.get("pn", "")

                # Extract section title
                title_elem = section.find("name")
                section_title = (
                    title_elem.text
                    if title_elem is not None
                    else f"Section {section_number}"
                )

                # Extract section content
                content_parts = []
                for elem in section.iter():
                    if elem.tag in ["t", "list", "figure", "texttable"]:
                        if elem.text:
                            content_parts.append(elem.text.strip())
                        for child in elem.itertext():
                            if child.strip():
                                content_parts.append(child.strip())

                excerpt = " ".join(content_parts)[:1000]  # Limit excerpt length

                if excerpt:
                    # Generate hash
                    normalized_text = (
                        f"{rfc_number}:{section_number}:{excerpt}".lower().strip()
                    )
                    content_hash = hashlib.sha256(
                        normalized_text.encode("utf-8")
                    ).hexdigest()

                    # Build URL
                    url = urljoin(
                        settings.rfc_mirror_url, f"rfc{rfc_number}.xml#{section_id}"
                    )

                    rfc_section = RFCSection(
                        rfc_number=rfc_number,
                        section=section_number,
                        title=section_title,
                        excerpt=excerpt,
                        url=url,
                        hash=content_hash,
                        built_at=datetime.utcnow(),
                    )
                    sections.append(rfc_section)

            self.logger.info(
                f"Sectionized RFC {rfc_number} into {len(sections)} sections"
            )
            return sections

        except etree.XMLSyntaxError as e:
            self.logger.error(f"XML parsing error for RFC {rfc_number}: {e}")
            raise RFCSyncError(f"Failed to parse RFC {rfc_number} XML: {e}")

    def sectionize_txt(self, txt_content: str, rfc_number: int) -> List[RFCSection]:
        """Sectionize an RFC text document (fallback method)."""
        sections = []
        lines = txt_content.split("\n")
        current_section = None
        current_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for section headers (e.g., "1. Introduction", "2.1. Protocol")
            if line and line[0].isdigit() and "." in line[:10]:
                # Save previous section
                if current_section and current_content:
                    excerpt = " ".join(current_content)[:1000]
                    if excerpt:
                        normalized_text = (
                            f"{rfc_number}:{current_section}:{excerpt}".lower().strip()
                        )
                        content_hash = hashlib.sha256(
                            normalized_text.encode("utf-8")
                        ).hexdigest()

                        url = urljoin(settings.rfc_mirror_url, f"rfc{rfc_number}.txt")

                        rfc_section = RFCSection(
                            rfc_number=rfc_number,
                            section=current_section,
                            title=current_section,
                            excerpt=excerpt,
                            url=url,
                            hash=content_hash,
                            built_at=datetime.utcnow(),
                        )
                        sections.append(rfc_section)

                # Start new section
                current_section = line.split()[0]  # Extract section number
                current_content = [line]
            else:
                if current_section:
                    current_content.append(line)

        # Save final section
        if current_section and current_content:
            excerpt = " ".join(current_content)[:1000]
            if excerpt:
                normalized_text = (
                    f"{rfc_number}:{current_section}:{excerpt}".lower().strip()
                )
                content_hash = hashlib.sha256(
                    normalized_text.encode("utf-8")
                ).hexdigest()

                url = urljoin(settings.rfc_mirror_url, f"rfc{rfc_number}.txt")

                rfc_section = RFCSection(
                    rfc_number=rfc_number,
                    section=current_section,
                    title=current_section,
                    excerpt=excerpt,
                    url=url,
                    hash=content_hash,
                    built_at=datetime.utcnow(),
                )
                sections.append(rfc_section)

        self.logger.info(
            f"Sectionized RFC {rfc_number} (text) into {len(sections)} sections"
        )
        return sections


class RFCSyncer:
    """Handles RFC synchronization from the official mirror."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.syncer")
        self.sectionizer = RFCSectionizer()
        self.client = httpx.AsyncClient(timeout=30.0)
        self.rfc_dir = settings.rfc_dir
        self.rfc_dir.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def download_rfc(
        self, rfc_number: int
    ) -> Tuple[Optional[str], Optional[str]]:
        """Download RFC in both XML and TXT formats."""
        xml_content = None
        txt_content = None

        # Try XML first
        xml_url = urljoin(settings.rfc_mirror_url, f"rfc{rfc_number}.xml")
        try:
            response = await self.client.get(xml_url)
            response.raise_for_status()
            xml_content = response.text
            self.logger.debug(f"Downloaded RFC {rfc_number} XML")
        except httpx.HTTPStatusError as e:
            self.logger.warning(f"Failed to download RFC {rfc_number} XML: {e}")

        # Try TXT as fallback
        txt_url = urljoin(settings.rfc_mirror_url, f"rfc{rfc_number}.txt")
        try:
            response = await self.client.get(txt_url)
            response.raise_for_status()
            txt_content = response.text
            self.logger.debug(f"Downloaded RFC {rfc_number} TXT")
        except httpx.HTTPStatusError as e:
            self.logger.warning(f"Failed to download RFC {rfc_number} TXT: {e}")

        if not xml_content and not txt_content:
            raise RFCSyncError(f"Failed to download RFC {rfc_number} in any format")

        return xml_content, txt_content

    def save_rfc_sections(self, sections: List[RFCSection]) -> None:
        """Save RFC sections to JSONL file."""
        rfc_index_file = self.rfc_dir / "rfc_index.jsonl"

        with open(rfc_index_file, "a", encoding="utf-8") as f:
            for section in sections:
                json_line = orjson.dumps(section.dict(), option=orjson.OPT_SORT_KEYS)
                f.write(json_line.decode("utf-8") + "\n")

        self.logger.info(f"Saved {len(sections)} sections to {rfc_index_file}")

    def create_manifest(self, sections: List[RFCSection]) -> Dict:
        """Create a manifest for the RFC sections."""
        manifest = {
            "created_at": datetime.utcnow().isoformat(),
            "total_sections": len(sections),
            "rfc_numbers": sorted(list(set(s.rfc_number for s in sections))),
            "section_hashes": [s.hash for s in sections],
            "manifest_hash": hashlib.sha256(
                json.dumps([s.hash for s in sections], sort_keys=True).encode("utf-8")
            ).hexdigest(),
        }

        manifest_file = self.rfc_dir / "manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)

        self.logger.info(f"Created manifest with {len(sections)} sections")
        return manifest

    async def sync_rfc(self, rfc_number: int) -> List[RFCSection]:
        """Sync a single RFC document."""
        self.logger.info(f"Syncing RFC {rfc_number}")

        # Download RFC
        xml_content, txt_content = await self.download_rfc(rfc_number)

        # Sectionize
        sections = []
        if xml_content:
            try:
                sections = self.sectionizer.sectionize_xml(xml_content, rfc_number)
            except RFCSyncError:
                self.logger.warning(
                    f"XML sectionization failed for RFC {rfc_number}, trying TXT"
                )

        if not sections and txt_content:
            sections = self.sectionizer.sectionize_txt(txt_content, rfc_number)

        if not sections:
            raise RFCSyncError(f"Failed to sectionize RFC {rfc_number}")

        # Save sections
        self.save_rfc_sections(sections)

        return sections

    async def sync_rfc_range(self, start: int, end: int) -> List[RFCSection]:
        """Sync a range of RFC documents."""
        all_sections = []

        for rfc_number in range(start, end + 1):
            try:
                sections = await self.sync_rfc(rfc_number)
                all_sections.extend(sections)
            except RFCSyncError as e:
                self.logger.error(f"Failed to sync RFC {rfc_number}: {e}")
                continue

        # Create manifest
        if all_sections:
            self.create_manifest(all_sections)

        return all_sections


async def main():
    """Main entry point for RFC synchronization."""

    logging.basicConfig(level=logging.INFO, format=settings.log_format)

    # Ensure directories exist
    settings.ensure_directories()

    async with RFCSyncer() as syncer:
        # Sync common networking RFCs
        common_rfcs = [
            826,  # ARP
            791,  # IPv4
            2460,  # IPv6
            2328,  # OSPF v2
            4271,  # BGP-4
            3031,  # MPLS
            826,  # ARP
            1034,  # DNS
            2131,  # DHCP
            826,  # ARP
        ]

        all_sections = []
        for rfc_number in common_rfcs:
            try:
                sections = await syncer.sync_rfc(rfc_number)
                all_sections.extend(sections)
            except RFCSyncError as e:
                logger.error(f"Failed to sync RFC {rfc_number}: {e}")

        logger.info(f"RFC sync completed. Total sections: {len(all_sections)}")


if __name__ == "__main__":
    asyncio.run(main())
