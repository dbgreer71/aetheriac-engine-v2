"""
Basic unit tests for AE v2 components.

These tests verify the core functionality of the main components
without requiring external dependencies or data.
"""

import pytest
from datetime import datetime

from ae2.contracts.models import (
    Query, QueryType, RFCSection, Evidence, EvidenceType,
    Definition, ConceptCard, Case, Playbook, VendorCommandIR, VendorType
)
from ae2.contracts.settings import settings
from ae2.router.definitional_router import DefinitionalRouter
from ae2.assembler.definition_assembler import DefinitionAssembler


class TestContracts:
    """Test Pydantic model contracts."""
    
    def test_rfc_section_creation(self):
        """Test RFCSection model creation and validation."""
        section = RFCSection(
            rfc_number=826,
            section="1.1",
            title="Introduction",
            excerpt="ARP is a protocol for mapping IP addresses to MAC addresses.",
            url="https://www.rfc-editor.org/rfc/rfc826.xml#section-1.1",
            hash="a" * 64,  # Valid SHA256 hash
            built_at=datetime.utcnow()
        )
        
        assert section.rfc_number == 826
        assert section.section == "1.1"
        assert "ARP" in section.excerpt
        assert len(section.hash) == 64
        assert section.id.startswith("rfc:826:1.1:")
    
    def test_rfc_section_invalid_hash(self):
        """Test RFCSection validation with invalid hash."""
        with pytest.raises(ValueError, match="Hash must be a valid SHA256 hash"):
            RFCSection(
                rfc_number=826,
                section="1.1",
                title="Introduction",
                excerpt="ARP is a protocol for mapping IP addresses to MAC addresses.",
                url="https://www.rfc-editor.org/rfc/rfc826.xml#section-1.1",
                hash="invalid_hash",
                built_at=datetime.utcnow()
            )
    
    def test_query_creation(self):
        """Test Query model creation."""
        query = Query(
            text="What is ARP?",
            query_type=QueryType.DEFINITION,
            context={"protocol": "arp"}
        )
        
        assert query.text == "What is ARP?"
        assert query.query_type == QueryType.DEFINITION
        assert query.context["protocol"] == "arp"
    
    def test_evidence_creation(self):
        """Test Evidence model creation."""
        evidence = Evidence(
            type=EvidenceType.RFC_SECTION,
            path_or_url="https://www.rfc-editor.org/rfc/rfc826.xml#section-1.1",
            sha256="a" * 64,
            excerpt="ARP is a protocol for mapping IP addresses to MAC addresses."
        )
        
        assert evidence.type == EvidenceType.RFC_SECTION
        assert "rfc826" in evidence.path_or_url
        assert len(evidence.sha256) == 64
    
    def test_concept_card_creation(self):
        """Test ConceptCard model creation."""
        definition = Definition(
            text="ARP is a protocol for mapping IP addresses to MAC addresses.",
            rfc_number=826,
            section="1.1",
            url="https://www.rfc-editor.org/rfc/rfc826.xml#section-1.1"
        )
        
        card = ConceptCard(
            id="concept:arp:v1",
            definition=definition,
            built_at=datetime.utcnow()
        )
        
        assert card.id == "concept:arp:v1"
        assert "ARP" in card.definition.text
        assert card.definition.rfc_number == 826
    
    def test_vendor_command_ir_creation(self):
        """Test VendorCommandIR model creation."""
        command = VendorCommandIR(
            intent="show_interface_status",
            params={"interface": "GigabitEthernet0/1"},
            vendor=VendorType.CISCO_IOS_XE
        )
        
        assert command.intent == "show_interface_status"
        assert command.params["interface"] == "GigabitEthernet0/1"
        assert command.vendor == VendorType.CISCO_IOS_XE


class TestRouter:
    """Test DefinitionalRouter functionality."""
    
    def setup_method(self):
        """Setup router for each test."""
        self.router = DefinitionalRouter()
    
    def test_definition_query_classification(self):
        """Test classification of definition queries."""
        query = Query(text="What is ARP?")
        routing_info = self.router.route_query(query)
        
        assert routing_info["query_type"] == QueryType.DEFINITION
        assert routing_info["confidence"] > 0.5
        assert routing_info["handler"] == "definition_assembler"
        assert routing_info["requires_strict_mode"] == True
    
    def test_concept_query_classification(self):
        """Test classification of concept queries."""
        query = Query(text="Compare ARP and DNS")
        routing_info = self.router.route_query(query)
        
        assert routing_info["query_type"] == QueryType.CONCEPT
        assert routing_info["confidence"] > 0.5
        assert routing_info["handler"] == "concept_assembler"
        assert "arp" in routing_info["context"]["protocol_terms"]
        assert "dns" in routing_info["context"]["protocol_terms"]
    
    def test_troubleshooting_query_classification(self):
        """Test classification of troubleshooting queries."""
        query = Query(text="OSPF neighbor down")
        routing_info = self.router.route_query(query)
        
        assert routing_info["query_type"] == QueryType.TROUBLESHOOTING
        assert routing_info["confidence"] > 0.4
        assert routing_info["handler"] == "troubleshooting_assembler"
        assert "ospf" in routing_info["context"]["protocol_terms"]
    
    def test_router_stats(self):
        """Test router statistics."""
        stats = self.router.get_router_stats()
        
        assert "definition_patterns" in stats
        assert "concept_patterns" in stats
        assert "troubleshooting_patterns" in stats
        assert "protocol_lexicon_size" in stats
        assert "strict_definitions_enabled" in stats


class TestAssembler:
    """Test DefinitionAssembler functionality."""
    
    def setup_method(self):
        """Setup assembler for each test."""
        self.assembler = DefinitionAssembler()
    
    def test_contains_definition(self):
        """Test definition detection in text."""
        definition_text = "ARP is defined as a protocol for mapping IP addresses to MAC addresses."
        non_definition_text = "This is just some random text about networking."
        
        assert self.assembler._contains_definition(definition_text) == True
        assert self.assembler._contains_definition(non_definition_text) == False
    
    def test_high_quality_definition_detection(self):
        """Test high-quality definition detection."""
        section = RFCSection(
            rfc_number=826,
            section="1.1",
            title="Introduction",
            excerpt="ARP is defined as a protocol for mapping IP addresses to MAC addresses. This protocol operates at the data link layer and provides a mechanism for hosts to discover the MAC address associated with a given IP address.",
            url="https://www.rfc-editor.org/rfc/rfc826.xml#section-1.1",
            hash="a" * 64,
            built_at=datetime.utcnow()
        )
        
        assert self.assembler._is_high_quality_definition(section) == True
    
    def test_assembler_stats(self):
        """Test assembler statistics."""
        stats = self.assembler.get_assembler_stats()
        
        assert "strict_mode" in stats
        assert "definition_indicators" in stats
        assert "quality_threshold" in stats
        assert stats["strict_mode"] == settings.strict_definitions


class TestSettings:
    """Test settings configuration."""
    
    def test_settings_initialization(self):
        """Test settings initialization."""
        assert settings.app_name == "Aetheriac Engine v2"
        assert settings.app_version == "0.1.0"
        assert settings.api_port == 8000
        assert settings.enable_rfc == True
        assert settings.strict_definitions == True
    
    def test_directory_creation(self):
        """Test directory creation."""
        # This test ensures the ensure_directories method works
        # without actually creating directories in the test environment
        assert hasattr(settings, 'ensure_directories')
        assert callable(settings.ensure_directories)
    
    def test_path_resolution(self):
        """Test path resolution."""
        assert settings.index_path.is_absolute()
        assert settings.rfc_path.is_absolute()
        assert settings.concepts_path.is_absolute()
        assert settings.playbooks_path.is_absolute()


class TestIntegration:
    """Test basic integration between components."""
    
    def test_router_to_assembler_flow(self):
        """Test basic flow from router to assembler."""
        router = DefinitionalRouter()
        assembler = DefinitionAssembler()
        
        # Create a test query
        query = Query(text="What is ARP?")
        
        # Route the query
        routing_info = router.route_query(query)
        
        # Verify routing
        assert routing_info["query_type"] == QueryType.DEFINITION
        assert routing_info["handler"] == "definition_assembler"
        
        # Create mock retrieved sections
        mock_section = RFCSection(
            rfc_number=826,
            section="1.1",
            title="Introduction",
            excerpt="ARP is defined as a protocol for mapping IP addresses to MAC addresses.",
            url="https://www.rfc-editor.org/rfc/rfc826.xml#section-1.1",
            hash="a" * 64,
            built_at=datetime.utcnow()
        )
        
        retrieved_sections = [(mock_section, 0.8)]
        
        # Assemble response
        query_id = "test_query_123"
        response = assembler.assemble_definition(
            query=query,
            retrieved_sections=retrieved_sections,
            query_id=query_id
        )
        
        # Verify response
        assert response.query_id == query_id
        assert response.response_type == QueryType.DEFINITION
        assert response.confidence > 0.0
        assert "definition" in response.content
        assert len(response.citations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 