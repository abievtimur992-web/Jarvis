"""
test_tools.py — tools.py ushın stdlib unittest testleri, ásirese
compute_finance (BUSINESS DECISION ENGINE 2-basqıshı) ushın.

Testler PROJECT-tiń nızıq memory/ papkasına HESH QASHAN JAZBAYDI — hár
test ózi ushın waqtıńsha (tempfile) papka jasaydı hám aqırında ózi
óshiredi.

Iske túsiriw: python test_tools.py  (yamasa: python -m unittest test_tools)
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import business as business_mod
import tools
import vault as vault_mod


class ComputeFinanceTestCase(unittest.TestCase):
    def _num(self, value, unit):
        return {"value": value, "unit": unit}


# ---------------------------------------------------------------------------
# Operatsiyalar — durıs esaplar
# ---------------------------------------------------------------------------


class TestOperationsSucceed(ComputeFinanceTestCase):
    def test_gross_profit(self):
        r = tools.compute_finance(
            "gross_profit",
            {"revenue": self._num(100000000, "UZS"), "cost": self._num(30000000, "UZS")},
        )
        self.assertEqual(r["card"]["result"], {"value": 70000000, "unit": "UZS"})
        self.assertNotIn("error", r["card"])

    def test_margin(self):
        r = tools.compute_finance(
            "margin",
            {"revenue": self._num(100000000, "UZS"), "cost": self._num(30000000, "UZS")},
        )
        self.assertEqual(r["card"]["result"], {"value": 70.0, "unit": "percent"})

    def test_average_check(self):
        r = tools.compute_finance(
            "average_check",
            {"revenue": self._num(100000000, "UZS"), "customers": self._num(80, "count")},
        )
        self.assertEqual(r["card"]["result"], {"value": 1250000, "unit": "UZS"})

    def test_growth_percent_positive(self):
        r = tools.compute_finance(
            "growth_percent",
            {"current": self._num(120000000, "UZS"), "previous": self._num(100000000, "UZS")},
        )
        self.assertEqual(r["card"]["result"], {"value": 20.0, "unit": "percent"})

    def test_growth_percent_negative(self):
        r = tools.compute_finance(
            "growth_percent",
            {"current": self._num(80000000, "UZS"), "previous": self._num(100000000, "UZS")},
        )
        self.assertEqual(r["card"]["result"]["value"], -20.0)

    def test_cash_flow_net(self):
        r = tools.compute_finance(
            "cash_flow_net",
            {
                "revenue": self._num(100000000, "UZS"),
                "cost": self._num(30000000, "UZS"),
                "fixed_costs": self._num(20000000, "UZS"),
            },
        )
        self.assertEqual(r["card"]["result"], {"value": 50000000, "unit": "UZS"})

    def test_percent_result_rounded_to_two_decimals(self):
        r = tools.compute_finance(
            "margin",
            {"revenue": self._num(3, "UZS"), "cost": self._num(1, "UZS")},
        )
        # (3-1)/3*100 = 66.666... -> 66.67
        self.assertEqual(r["card"]["result"]["value"], 66.67)

    def test_spoken_is_short_and_present(self):
        r = tools.compute_finance(
            "gross_profit",
            {"revenue": self._num(100000000, "UZS"), "cost": self._num(30000000, "UZS")},
        )
        self.assertTrue(r["spoken"])
        self.assertLess(len(r["spoken"]), 200)


# ---------------------------------------------------------------------------
# Nolge bóliw qorǵawı
# ---------------------------------------------------------------------------


class TestDivisionByZero(ComputeFinanceTestCase):
    def test_margin_zero_revenue(self):
        r = tools.compute_finance(
            "margin", {"revenue": self._num(0, "UZS"), "cost": self._num(10, "UZS")}
        )
        self.assertIn("error", r["card"])

    def test_average_check_zero_customers(self):
        r = tools.compute_finance(
            "average_check", {"revenue": self._num(100, "UZS"), "customers": self._num(0, "count")}
        )
        self.assertIn("error", r["card"])

    def test_growth_percent_zero_previous(self):
        r = tools.compute_finance(
            "growth_percent", {"current": self._num(100, "UZS"), "previous": self._num(0, "UZS")}
        )
        self.assertIn("error", r["card"])

    def test_no_nan_or_infinity_ever_returned(self):
        for op, inp in [
            ("margin", {"revenue": self._num(0, "UZS"), "cost": self._num(10, "UZS")}),
            ("average_check", {"revenue": self._num(1, "UZS"), "customers": self._num(0, "count")}),
            ("growth_percent", {"current": self._num(1, "UZS"), "previous": self._num(0, "UZS")}),
        ]:
            r = tools.compute_finance(op, inp)
            self.assertNotIn("result", r["card"])


# ---------------------------------------------------------------------------
# Unit sáykessizligi
# ---------------------------------------------------------------------------


class TestUnitMismatch(ComputeFinanceTestCase):
    def test_gross_profit_currency_mismatch(self):
        r = tools.compute_finance(
            "gross_profit",
            {"revenue": self._num(100, "UZS"), "cost": self._num(10, "USD")},
        )
        self.assertIn("error", r["card"])
        self.assertNotIn("result", r["card"])

    def test_cash_flow_net_currency_mismatch(self):
        r = tools.compute_finance(
            "cash_flow_net",
            {
                "revenue": self._num(100, "UZS"),
                "cost": self._num(10, "UZS"),
                "fixed_costs": self._num(5, "KZT"),
            },
        )
        self.assertIn("error", r["card"])

    def test_growth_percent_unit_mismatch(self):
        r = tools.compute_finance(
            "growth_percent",
            {"current": self._num(100, "UZS"), "previous": self._num(80, "count")},
        )
        self.assertIn("error", r["card"])

    def test_average_check_customers_wrong_unit(self):
        r = tools.compute_finance(
            "average_check",
            {"revenue": self._num(100, "UZS"), "customers": self._num(10, "UZS")},
        )
        self.assertIn("error", r["card"])

    def test_no_currency_conversion_performed(self):
        # Tool "80" -di "80 USD" dep aldın ala almaydı, tek qátelik beredi —
        # exchange rate hesh qashan ózinen oylap tabılmaydı.
        r = tools.compute_finance(
            "gross_profit",
            {"revenue": self._num(100, "USD"), "cost": self._num(80, "UZS")},
        )
        self.assertIn("error", r["card"])
        self.assertNotIn("result", r["card"])


# ---------------------------------------------------------------------------
# Jaramsız/joq input
# ---------------------------------------------------------------------------


class TestInvalidInput(ComputeFinanceTestCase):
    def test_unknown_operation(self):
        r = tools.compute_finance("net_present_value", {})
        self.assertIn("error", r["card"])

    def test_missing_required_input(self):
        r = tools.compute_finance("gross_profit", {"revenue": self._num(100, "UZS")})
        self.assertIn("error", r["card"])
        self.assertIn("cost", r["card"]["error"])

    def test_non_numeric_value_rejected(self):
        r = tools.compute_finance(
            "gross_profit",
            {"revenue": self._num("100 mln som", "UZS"), "cost": self._num(10, "UZS")},
        )
        self.assertIn("error", r["card"])

    def test_missing_unit_rejected(self):
        r = tools.compute_finance(
            "gross_profit",
            {"revenue": {"value": 100}, "cost": self._num(10, "UZS")},
        )
        self.assertIn("error", r["card"])

    def test_unrecognized_unit_rejected(self):
        r = tools.compute_finance(
            "gross_profit",
            {"revenue": self._num(100, "som"), "cost": self._num(10, "UZS")},
        )
        self.assertIn("error", r["card"])

    def test_bool_value_rejected(self):
        r = tools.compute_finance(
            "gross_profit",
            {"revenue": self._num(True, "UZS"), "cost": self._num(10, "UZS")},
        )
        self.assertIn("error", r["card"])

    def test_none_inputs_does_not_crash(self):
        r = tools.compute_finance("gross_profit", None)
        self.assertIn("error", r["card"])

    def test_empty_operation_does_not_crash(self):
        r = tools.compute_finance("", {})
        self.assertIn("error", r["card"])


# ---------------------------------------------------------------------------
# Qáwipsizlik: filesystem-ge tiymeydi
# ---------------------------------------------------------------------------


class TestNoSideEffects(ComputeFinanceTestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="jarvis_test_tools_")
        self.memory_dir = Path(self._tmp)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_compute_finance_writes_nothing_to_disk(self):
        before = list(Path(self.memory_dir).rglob("*"))
        tools.compute_finance(
            "gross_profit",
            {"revenue": self._num(100000000, "UZS"), "cost": self._num(30000000, "UZS")},
        )
        tools.compute_finance("margin", {"revenue": self._num(0, "UZS"), "cost": self._num(1, "UZS")})
        after = list(Path(self.memory_dir).rglob("*"))
        self.assertEqual(before, after)
        self.assertEqual(after, [])

    def _num(self, value, unit):
        return {"value": value, "unit": unit}


# ---------------------------------------------------------------------------
# run_tool() dispetcher arqalı (compute_finance + regression basqa 5 tool)
# ---------------------------------------------------------------------------


class TestRunToolDispatcher(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="jarvis_test_tools_dispatch_")
        self.memory_dir = Path(self._tmp)
        self.ctx = {"vault": vault_mod.Vault(), "profile": {}, "memory_dir": self.memory_dir}

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_run_tool_compute_finance(self):
        result = tools.run_tool(
            "compute_finance",
            {
                "operation": "gross_profit",
                "inputs": {"revenue": {"value": 100, "unit": "UZS"}, "cost": {"value": 40, "unit": "UZS"}},
            },
            self.ctx,
        )
        self.assertEqual(result["card"]["result"]["value"], 60)

    def test_run_tool_unknown_name_still_handled(self):
        result = tools.run_tool("not_a_real_tool", {}, self.ctx)
        self.assertIn("error", result["card"])

    def test_run_tool_search_brain_unaffected(self):
        result = tools.run_tool("search_brain", {"query": "ARKAN"}, self.ctx)
        self.assertEqual(result["card"]["tool"], "search_brain")

    def test_run_tool_remember_unaffected(self):
        result = tools.run_tool("remember", {"fact": "sınaw jazbası"}, self.ctx)
        self.assertEqual(result["card"]["tool"], "remember")
        self.assertEqual(result["card"]["kind"], "personal_memory")

    def test_run_tool_plan_day_unaffected(self):
        result = tools.run_tool("plan_day", {}, self.ctx)
        self.assertEqual(result["card"]["tool"], "plan_day")

    def test_run_tool_brief_me_unaffected(self):
        result = tools.run_tool("brief_me", {}, self.ctx)
        self.assertEqual(result["card"]["tool"], "brief_me")

    def test_run_tool_remember_numeric_value_and_unit_passthrough(self):
        result = tools.run_tool(
            "remember",
            {"business": "ARKAN", "field": "finance.revenue", "fact": "100 mln som", "value": 100000000, "unit": "UZS"},
            self.ctx,
        )
        self.assertEqual(result["card"]["operation"], "numeric")
        self.assertEqual(result["card"]["value"], 100000000)
        self.assertEqual(result["card"]["unit"], "UZS")


# ---------------------------------------------------------------------------
# remember() — NUMERIC integratsiya (BUSINESS DECISION ENGINE 3-basqısh)
# ---------------------------------------------------------------------------


class RememberNumericTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="jarvis_test_remember_numeric_")
        self.memory_dir = Path(self._tmp)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _raw_json(self, business_name: str) -> dict:
        import business as business_mod
        import json as json_mod

        path = self.memory_dir / "business_data" / f"{business_mod._slugify(business_name)}.json"
        return json_mod.loads(path.read_text(encoding="utf-8"))


class TestRememberNumericSave(RememberNumericTestCase):
    def test_numeric_value_and_unit_saved_structurally(self):
        result = tools.remember(
            self.memory_dir, "ARKAN-nıń aylıq kirimi 20 mln som", business="ARKAN",
            field="finance.revenue", value=20000000, unit="UZS",
        )
        self.assertEqual(result["card"]["operation"], "numeric")
        self.assertNotIn("error", result["card"])
        entry = self._raw_json("ARKAN")["fields"]["finance"]["revenue"]
        self.assertEqual(entry["value"], 20000000)
        self.assertEqual(entry["unit"], "UZS")

    def test_missing_unit_defaults_to_unknown(self):
        result = tools.remember(
            self.memory_dir, "ARKAN-nıń aylıq kirimi 20 mln", business="ARKAN",
            field="finance.revenue", value=20000000,
        )
        self.assertNotIn("error", result["card"])
        entry = self._raw_json("ARKAN")["fields"]["finance"]["revenue"]
        self.assertEqual(entry["unit"], "unknown")

    def test_update_keeps_previous(self):
        tools.remember(self.memory_dir, "20 mln", business="ARKAN", field="finance.revenue", value=20000000, unit="UZS")
        tools.remember(self.memory_dir, "25 mln", business="ARKAN", field="finance.revenue", value=25000000, unit="UZS")
        entry = self._raw_json("ARKAN")["fields"]["finance"]["revenue"]
        self.assertEqual(entry["value"], 25000000)
        self.assertEqual(entry["previous"]["value"], 20000000)


class TestRememberNumericBackwardCompat(RememberNumericTestCase):
    def test_no_value_uses_old_text_path_unchanged(self):
        # value berilmese — eski jol (set_field, tekst) tolıq ózgerissiz.
        result = tools.remember(
            self.memory_dir, "100 mln som", business="ARKAN", field="finance.revenue",
        )
        self.assertEqual(result["card"]["kind"], "business_data")
        self.assertEqual(result["card"]["operation"], "replace")
        entry = self._raw_json("ARKAN")["fields"]["finance"]["revenue"]
        self.assertEqual(entry["value"], "100 mln som")
        self.assertNotIn("unit", entry)

    def test_scalar_field_without_value_unaffected(self):
        result = tools.remember(self.memory_dir, "granit tas", business="ESTELIK", field="products.categories")
        self.assertEqual(result["card"]["operation"], "replace")

    def test_list_append_without_value_unaffected(self):
        result = tools.remember(
            self.memory_dir, "lazer stanogı", business="ARKAN", field="products.equipment", append=True,
        )
        self.assertEqual(result["card"]["operation"], "append")
        entry = self._raw_json("ARKAN")["fields"]["products"]["equipment"]
        self.assertEqual(entry["value"], ["lazer stanogı"])

    def test_personal_memory_path_unaffected(self):
        result = tools.remember(self.memory_dir, "sınaw jazbası")
        self.assertEqual(result["card"]["kind"], "personal_memory")

    def test_business_knowledge_path_unaffected(self):
        result = tools.remember(self.memory_dir, "jańa josparı bar", business="TENAZ")
        self.assertEqual(result["card"]["kind"], "business_knowledge")


class TestRememberNumericValidation(RememberNumericTestCase):
    def test_value_on_non_numeric_field_rejected(self):
        result = tools.remember(
            self.memory_dir, "granit tas", business="ESTELIK", field="products.categories", value=5,
        )
        self.assertIn("error", result["card"])
        self.assertFalse((self.memory_dir / "business_data" / "estelik.json").exists())

    def test_value_on_list_field_rejected(self):
        result = tools.remember(
            self.memory_dir, "5 dana", business="ARKAN", field="products.equipment", value=5, unit="count",
        )
        self.assertIn("error", result["card"])

    def test_non_numeric_value_rejected(self):
        result = tools.remember(
            self.memory_dir, "kop som", business="ARKAN", field="finance.revenue", value="kop", unit="UZS",
        )
        self.assertIn("error", result["card"])

    def test_bool_value_rejected(self):
        result = tools.remember(
            self.memory_dir, "iya", business="ARKAN", field="finance.revenue", value=True, unit="UZS",
        )
        self.assertIn("error", result["card"])

    def test_unrecognized_unit_rejected(self):
        result = tools.remember(
            self.memory_dir, "20 mln som", business="ARKAN", field="finance.revenue", value=20000000, unit="som",
        )
        self.assertIn("error", result["card"])

    def test_negative_revenue_rejected(self):
        result = tools.remember(
            self.memory_dir, "-5 mln", business="ARKAN", field="finance.revenue", value=-5000000, unit="UZS",
        )
        self.assertIn("error", result["card"])

    def test_negative_cash_flow_allowed(self):
        result = tools.remember(
            self.memory_dir, "-5 mln", business="ARKAN", field="finance.cash_flow", value=-5000000, unit="UZS",
        )
        self.assertNotIn("error", result["card"])

    def test_negative_gross_margin_allowed(self):
        result = tools.remember(
            self.memory_dir, "-10%", business="ARKAN", field="finance.gross_margin", value=-10, unit="percent",
        )
        self.assertNotIn("error", result["card"])

    def test_invalid_write_does_not_create_file(self):
        tools.remember(self.memory_dir, "kop som", business="POLAT_TEST", field="finance.revenue", value="kop", unit="UZS")
        self.assertFalse((self.memory_dir / "business_data" / "polat_test.json").exists())


# ---------------------------------------------------------------------------
# TOOL_DEFINITIONS regressiyası
# ---------------------------------------------------------------------------


class TestToolDefinitionsRegression(unittest.TestCase):
    def test_all_eight_tools_registered(self):
        names = [t["name"] for t in tools.TOOL_DEFINITIONS]
        self.assertEqual(
            names,
            [
                "search_brain",
                "research_web",
                "remember",
                "plan_day",
                "brief_me",
                "compute_finance",
                "diagnose_business",
                "instagram_insights",
            ],
        )

    def test_existing_five_tool_schemas_untouched_shape(self):
        by_name = {t["name"]: t for t in tools.TOOL_DEFINITIONS}
        self.assertIn("query", by_name["search_brain"]["input_schema"]["properties"])
        self.assertIn("fact", by_name["remember"]["input_schema"]["properties"])
        self.assertIn("business", by_name["remember"]["input_schema"]["properties"])
        self.assertIn("field", by_name["remember"]["input_schema"]["properties"])
        self.assertIn("append", by_name["remember"]["input_schema"]["properties"])

    def test_compute_finance_schema_has_operation_enum(self):
        by_name = {t["name"]: t for t in tools.TOOL_DEFINITIONS}
        enum = by_name["compute_finance"]["input_schema"]["properties"]["operation"]["enum"]
        self.assertEqual(
            sorted(enum),
            ["average_check", "cash_flow_net", "gross_profit", "growth_percent", "margin"],
        )

    def test_remember_schema_has_numeric_value_and_unit(self):
        by_name = {t["name"]: t for t in tools.TOOL_DEFINITIONS}
        props = by_name["remember"]["input_schema"]["properties"]
        self.assertIn("value", props)
        self.assertIn("unit", props)
        self.assertEqual(props["value"]["type"], "number")
        self.assertEqual(sorted(props["unit"]["enum"]), sorted(["UZS", "USD", "KZT", "percent", "count"]))
        # 'fact' ele MINDETLI (backward compatible — hesh nárse alıp taslanbadı)
        self.assertEqual(by_name["remember"]["input_schema"]["required"], ["fact"])

    def test_diagnose_business_registered_read_only_description(self):
        by_name = {t["name"]: t for t in tools.TOOL_DEFINITIONS}
        self.assertIn("diagnose_business", by_name)
        props = by_name["diagnose_business"]["input_schema"]["properties"]
        self.assertEqual(set(props.keys()), {"business"})
        self.assertEqual(by_name["diagnose_business"]["input_schema"]["required"], ["business"])

    def test_instagram_insights_registered_no_input(self):
        by_name = {t["name"]: t for t in tools.TOOL_DEFINITIONS}
        self.assertIn("instagram_insights", by_name)
        self.assertEqual(by_name["instagram_insights"]["input_schema"]["properties"], {})


# ---------------------------------------------------------------------------
# instagram_insights — .env sazlanbaǵanda hesh nárse oylap tappaydı
# ---------------------------------------------------------------------------


class InstagramInsightsTestCase(unittest.TestCase):
    def setUp(self):
        self._saved = {
            k: os.environ.pop(k, None)
            for k in ("INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_BUSINESS_ACCOUNT_ID")
        }

    def tearDown(self):
        for k, v in self._saved.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)

    def test_not_configured_reports_clearly_no_crash(self):
        result = tools.instagram_insights()
        self.assertEqual(result["card"]["tool"], "instagram_insights")
        self.assertEqual(result["card"]["error"], "sazlanbaǵan")
        self.assertIn("sazlanbaǵan", result["spoken"])

    def test_missing_only_business_account_id_still_not_configured(self):
        os.environ["INSTAGRAM_ACCESS_TOKEN"] = "sınaw-token"
        result = tools.instagram_insights()
        self.assertEqual(result["card"]["error"], "sazlanbaǵan")

    def test_run_tool_dispatcher_wires_instagram_insights(self):
        ctx = {"vault": None, "profile": {}, "memory_dir": Path(tempfile.mkdtemp())}
        try:
            result = tools.run_tool("instagram_insights", {}, ctx)
            self.assertEqual(result["card"]["tool"], "instagram_insights")
        finally:
            shutil.rmtree(ctx["memory_dir"], ignore_errors=True)


# ---------------------------------------------------------------------------
# diagnose_business — BUSINESS DECISION ENGINE 2b-basqısh
# ---------------------------------------------------------------------------


class DiagnoseBusinessTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="jarvis_test_diagnose_")
        self.memory_dir = Path(self._tmp)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _raw_json(self, business_name: str) -> dict:
        path = self.memory_dir / "business_data" / f"{business_mod._slugify(business_name)}.json"
        return json.loads(path.read_text(encoding="utf-8"))


# A. tolıq numeric data bar business
class TestDiagnoseFullData(DiagnoseBusinessTestCase):
    def setUp(self):
        super().setUp()
        for key, val, unit in [
            ("finance.revenue", 120000000, "UZS"),
            ("finance.cost", 40000000, "UZS"),
            ("finance.gross_margin", 66.67, "percent"),
            ("finance.fixed_costs", 10000000, "UZS"),
            ("finance.cash_flow", 70000000, "UZS"),
            ("sales.monthly_sales", 120000000, "UZS"),
            ("sales.average_check", 1500000, "UZS"),
            ("customers.average_monthly_customers", 80, "count"),
        ]:
            business_mod.set_numeric_field(self.memory_dir, "ARKAN", key, val, unit)
        self.result = tools.diagnose_business(self.memory_dir, "ARKAN")

    def test_all_fields_verified(self):
        self.assertEqual(len(self.result["card"]["verified_data"]), 8)
        self.assertEqual(self.result["card"]["missing_fields"], [])

    def test_data_quality_full(self):
        self.assertEqual(self.result["card"]["data_quality"], "full")

    def test_four_direct_calculations_succeed(self):
        calc = self.result["card"]["calculations"]
        for op in ("gross_profit", "margin", "average_check", "cash_flow_net"):
            self.assertIn(op, calc)
        self.assertNotIn("growth_percent", calc)  # hesh bir field-de previous joq (bir ret jazılǵan)

    def test_no_calculation_gaps_for_direct_ops(self):
        gaps = [g["calculation"] for g in self.result["card"]["calculation_gaps"] if g["calculation"] != "growth_percent"]
        self.assertEqual(gaps, [])


# B. tek 2-3 numeric field bar business
class TestDiagnosePartialData(DiagnoseBusinessTestCase):
    def setUp(self):
        super().setUp()
        business_mod.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        business_mod.set_numeric_field(self.memory_dir, "ARKAN", "finance.cost", 30000000, "UZS")
        self.result = tools.diagnose_business(self.memory_dir, "ARKAN")

    def test_two_fields_verified_six_missing(self):
        card = self.result["card"]
        self.assertEqual(len(card["verified_data"]), 2)
        self.assertEqual(len(card["missing_fields"]), 6)

    def test_data_quality_partial(self):
        self.assertEqual(self.result["card"]["data_quality"], "partial")

    def test_gross_profit_and_margin_succeed(self):
        calc = self.result["card"]["calculations"]
        self.assertEqual(calc["gross_profit"]["value"], 70000000)
        self.assertAlmostEqual(calc["margin"]["value"], 70.0)

    def test_average_check_and_cash_flow_are_gaps(self):
        gap_ops = {g["calculation"] for g in self.result["card"]["calculation_gaps"]}
        self.assertIn("average_check", gap_ops)
        self.assertIn("cash_flow_net", gap_ops)


# C. barlıq numeric dana bos (business bar, tek numeric emes maydan)
class TestDiagnoseEmptyNumericData(DiagnoseBusinessTestCase):
    def setUp(self):
        super().setUp()
        business_mod.set_field(self.memory_dir, "TENAZ", "problems.operational_problems", "jańa satıwshı ketip qaldı")
        self.result = tools.diagnose_business(self.memory_dir, "TENAZ")

    def test_verified_data_empty(self):
        self.assertEqual(self.result["card"]["verified_data"], {})

    def test_all_eight_missing(self):
        self.assertEqual(len(self.result["card"]["missing_fields"]), 8)

    def test_data_quality_empty(self):
        self.assertEqual(self.result["card"]["data_quality"], "empty")

    def test_all_direct_calculations_are_gaps(self):
        gap_ops = {g["calculation"] for g in self.result["card"]["calculation_gaps"]}
        for op in ("gross_profit", "margin", "average_check", "cash_flow_net"):
            self.assertIn(op, gap_ops)

    def test_no_writes_to_disk(self):
        # diagnose_business READ-ONLY — set_field() jazǵan fayldan basqa
        # hesh nárse ózgermewi kerek.
        before = self._raw_json("TENAZ")
        tools.diagnose_business(self.memory_dir, "TENAZ")
        after = self._raw_json("TENAZ")
        self.assertEqual(before, after)


# D. belgisiz business (business_data-da mudam joq)
class TestDiagnoseUnknownBusiness(DiagnoseBusinessTestCase):
    def test_unknown_business_returns_empty_shape_no_crash(self):
        result = tools.diagnose_business(self.memory_dir, "JOQ_BIZNES")
        card = result["card"]
        self.assertEqual(card["business"], "JOQ_BIZNES")
        self.assertEqual(card["verified_data"], {})
        self.assertEqual(len(card["missing_fields"]), 8)
        self.assertEqual(card["data_quality"], "empty")

    def test_unknown_business_creates_no_business_json_file(self):
        # Eskertiw: business.py-diń _business_data_dir() oqıwda da
        # 'business_data/' PAPKASIN (bos bolsa da) jaratadı — bul
        # business.py-diń bar (usı fazada ózgertilmegen) minez-qulqı.
        # Nızıq tekseriw — JOQ_BIZNES ushın hesh qanday .json FAYL
        # jaratılmawı kerek (READ-ONLY kepilligi usı jerde).
        tools.diagnose_business(self.memory_dir, "JOQ_BIZNES")
        self.assertFalse((self.memory_dir / "business_data" / "joq_biznes.json").exists())

    def test_empty_business_name_handled_cleanly(self):
        result = tools.diagnose_business(self.memory_dir, "")
        self.assertIn("error", result["card"])


# E. unit sáykessizligi
class TestDiagnoseUnitMismatch(DiagnoseBusinessTestCase):
    def setUp(self):
        super().setUp()
        business_mod.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        business_mod.set_numeric_field(self.memory_dir, "ARKAN", "finance.cost", 40000000, "USD")
        self.result = tools.diagnose_business(self.memory_dir, "ARKAN")

    def test_both_fields_still_verified(self):
        # diagnose_business ÓZI unit-ti tekserip, verified_data-dan
        # ıshıqlap taslamaydı — bul compute_finance-tiń jumısı.
        self.assertIn("finance.revenue", self.result["card"]["verified_data"])
        self.assertIn("finance.cost", self.result["card"]["verified_data"])

    def test_gross_profit_and_margin_are_gaps_with_reason(self):
        by_op = {g["calculation"]: g for g in self.result["card"]["calculation_gaps"] if "field" not in g}
        self.assertIn("gross_profit", by_op)
        self.assertIn("sáykes kelmeydi", by_op["gross_profit"]["reason"])
        self.assertIn("margin", by_op)


# F. previous bar / G. previous joq
class TestDiagnoseGrowthPercent(DiagnoseBusinessTestCase):
    def test_growth_computed_when_previous_present(self):
        business_mod.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        business_mod.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 120000000, "UZS")
        result = tools.diagnose_business(self.memory_dir, "ARKAN")
        growth = result["card"]["calculations"].get("growth_percent", {})
        self.assertAlmostEqual(growth["finance.revenue"]["value"], 20.0)

    def test_growth_gap_when_no_previous(self):
        business_mod.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        result = tools.diagnose_business(self.memory_dir, "ARKAN")
        self.assertNotIn("growth_percent", result["card"]["calculations"])
        gaps = [g for g in result["card"]["calculation_gaps"] if g["calculation"] == "growth_percent"]
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["field"], "finance.revenue")


# H. zero/invalid value
class TestDiagnoseZeroInvalidValue(DiagnoseBusinessTestCase):
    def test_zero_customers_average_check_is_gap(self):
        business_mod.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        business_mod.set_numeric_field(self.memory_dir, "ARKAN", "customers.average_monthly_customers", 0, "count")
        result = tools.diagnose_business(self.memory_dir, "ARKAN")
        gap_ops = {g["calculation"] for g in result["card"]["calculation_gaps"]}
        self.assertIn("average_check", gap_ops)

    def test_zero_revenue_margin_is_gap(self):
        business_mod.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 0, "UZS")
        business_mod.set_numeric_field(self.memory_dir, "ARKAN", "finance.cost", 10, "UZS")
        result = tools.diagnose_business(self.memory_dir, "ARKAN")
        gap_ops = {g["calculation"] for g in result["card"]["calculation_gaps"]}
        self.assertIn("margin", gap_ops)

    def test_legacy_text_numeric_field_treated_as_missing(self):
        # Eski set_field() arqalı jazılǵan TEKST (unit joq) — verified_data-ǵa
        # EMES, missing_fields-ke túsiwi kerek (compute_finance-ke jaramsız).
        business_mod.set_field(self.memory_dir, "ARKAN", "finance.revenue", "100 mln som")
        result = tools.diagnose_business(self.memory_dir, "ARKAN")
        self.assertNotIn("finance.revenue", result["card"]["verified_data"])
        self.assertIn("finance.revenue", result["card"]["missing_fields"])


# I/J. demo/real mode — diagnose_business memory_dir-di basqa tool-lar
# menen BIRDEY aladı, ózinshe jańa demo-ajıratıw jasamaydı.
class TestDiagnoseDemoRealModePassthrough(unittest.TestCase):
    def setUp(self):
        self._demo_tmp = tempfile.mkdtemp(prefix="jarvis_test_diagnose_demo_")
        self._real_tmp = tempfile.mkdtemp(prefix="jarvis_test_diagnose_real_")

    def tearDown(self):
        shutil.rmtree(self._demo_tmp, ignore_errors=True)
        shutil.rmtree(self._real_tmp, ignore_errors=True)

    def test_uses_whatever_memory_dir_is_passed_no_special_casing(self):
        demo_dir = Path(self._demo_tmp)
        real_dir = Path(self._real_tmp)
        business_mod.set_numeric_field(demo_dir, "AMANAT", "finance.revenue", 5000000, "UZS")
        business_mod.set_numeric_field(real_dir, "ARKAN", "finance.revenue", 100000000, "UZS")

        demo_result = tools.diagnose_business(demo_dir, "AMANAT")
        real_result = tools.diagnose_business(real_dir, "ARKAN")

        self.assertEqual(demo_result["card"]["verified_data"]["finance.revenue"]["value"], 5000000)
        self.assertEqual(real_result["card"]["verified_data"]["finance.revenue"]["value"], 100000000)
        # eki ortasında qatnas joq — biri ekinshisiniń derekin kórmeydi
        self.assertEqual(tools.diagnose_business(demo_dir, "ARKAN")["card"]["verified_data"], {})
        self.assertEqual(tools.diagnose_business(real_dir, "AMANAT")["card"]["verified_data"], {})

    def test_run_tool_dispatcher_does_not_pass_profile_or_vault(self):
        ctx = {
            "vault": vault_mod.Vault(),
            "profile": {"businesses": [{"brand": "ARKAN", "prices": {"note": "eskerte", "x": "999999999"}}]},
            "memory_dir": Path(self._real_tmp),
        }
        result = tools.run_tool("diagnose_business", {"business": "ARKAN"}, ctx)
        # profile-dagi 999999999 hesh qashan verified_data-ǵa shıqpaydı —
        # business_data-da ARKAN ushın hesh nárse joq bolǵanı ushın.
        self.assertEqual(result["card"]["verified_data"], {})
        self.assertEqual(result["card"]["data_quality"], "empty")


# Regression: diagnose_business barlıq basqa tool-lardı BUZBAYDI, read-only
class TestDiagnoseBusinessRegression(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="jarvis_test_diagnose_regr_")
        self.memory_dir = Path(self._tmp)
        self.ctx = {"vault": vault_mod.Vault(), "profile": {}, "memory_dir": self.memory_dir}

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_run_tool_diagnose_business_via_dispatcher(self):
        business_mod.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        result = tools.run_tool("diagnose_business", {"business": "ARKAN"}, self.ctx)
        self.assertEqual(result["card"]["tool"], "diagnose_business")
        self.assertIn("finance.revenue", result["card"]["verified_data"])

    def test_compute_finance_unaffected(self):
        result = tools.compute_finance("gross_profit", {"revenue": {"value": 100, "unit": "UZS"}, "cost": {"value": 40, "unit": "UZS"}})
        self.assertEqual(result["card"]["result"]["value"], 60)

    def test_remember_unaffected(self):
        result = tools.run_tool("remember", {"fact": "sınaw"}, self.ctx)
        self.assertEqual(result["card"]["kind"], "personal_memory")

    def test_search_brain_unaffected(self):
        result = tools.run_tool("search_brain", {"query": "ARKAN"}, self.ctx)
        self.assertEqual(result["card"]["tool"], "search_brain")

    def test_diagnose_business_writes_nothing(self):
        business_mod.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        path = self.memory_dir / "business_data" / "arkan.json"
        before = path.read_text(encoding="utf-8")
        tools.run_tool("diagnose_business", {"business": "ARKAN"}, self.ctx)
        after = path.read_text(encoding="utf-8")
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
