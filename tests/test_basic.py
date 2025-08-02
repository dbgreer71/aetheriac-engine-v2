# tests/test_basic.py
from ae2.contracts.models import Query
from ae2.router.definitional_router import DefinitionalRouter


class TestRouter:
    def test_route_simple(self):
        router = DefinitionalRouter()
        q = Query(text="what is ospf", query_type="definition")
        route = router.route_query(q)
        assert route.intent == "DEFINE"
        assert "ospf" in route.normalized_terms


class TestIntegration:
    def test_dns_term_present(self):
        router = DefinitionalRouter()
        q = Query(text="explain dns", query_type="definition")
        route = router.route_query(q)
        assert "dns" in route.normalized_terms
