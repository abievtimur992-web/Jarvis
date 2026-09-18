"""
test_business.py — business.py ushın stdlib unittest testleri, ásirese
NUMERIC BUSINESS DATA STORAGE (set_numeric_field) mexanizmi ushın —
BUSINESS DECISION ENGINE-diń 1-basqıshı.

Testler PROJECT-tiń nızıq memory/ papkasına HESH QASHAN JAZBAYDI — hár
test ózi ushın waqtıńsha (tempfile) papka jasaydı hám aqırında ózi
óshiredi. Bul Timurdıń haqıyqıy biznes maǵlıwmatın qáwipsiz saqlaydı.

Iske túsiriw: python test_business.py  (yamasa: python -m unittest test_business)
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import business


class BusinessTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="jarvis_test_business_")
        self.memory_dir = Path(self._tmp)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _raw_json(self, business_name: str) -> dict:
        path = self.memory_dir / "business_data" / f"{business._slugify(business_name)}.json"
        return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1) NUMERIC field — jazıw (save)
# ---------------------------------------------------------------------------


class TestNumericFieldSave(BusinessTestCase):
    def test_numeric_field_save(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        data = self._raw_json("ARKAN")
        entry = data["fields"]["finance"]["revenue"]
        self.assertEqual(entry["value"], 100000000)
        self.assertIsInstance(entry["value"], int)

    def test_numeric_field_save_with_string_input(self):
        # "100000000" (tekst, biraq TOLIQ sandan turatuǵın) — qabıl etiledi.
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.cost", "30000000", "UZS")
        data = self._raw_json("ARKAN")
        self.assertEqual(data["fields"]["finance"]["cost"]["value"], 30000000)

    def test_numeric_field_save_float(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.gross_margin", 23.5, "percent")
        data = self._raw_json("ARKAN")
        self.assertEqual(data["fields"]["finance"]["gross_margin"]["value"], 23.5)


# ---------------------------------------------------------------------------
# 2) NUMERIC field — oqıw (read) hám load_business arqalı
# ---------------------------------------------------------------------------


class TestNumericFieldRead(BusinessTestCase):
    def test_numeric_field_read_via_load_business(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        data = business.load_business(self.memory_dir, "ARKAN")
        entry = data["fields"]["finance"]["revenue"]
        self.assertEqual(entry["value"], 100000000)
        self.assertEqual(entry["unit"], "UZS")

    def test_numeric_field_in_format_business_summary(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        data = business.load_business(self.memory_dir, "ARKAN")
        summary = business.format_business_summary(data)
        self.assertIn("100000000", summary)
        self.assertIn("UZS", summary)


# ---------------------------------------------------------------------------
# 3) unit saqlaw
# ---------------------------------------------------------------------------


class TestUnitSave(BusinessTestCase):
    def test_unit_save_uzs(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        entry = self._raw_json("ARKAN")["fields"]["finance"]["revenue"]
        self.assertEqual(entry["unit"], "UZS")

    def test_unit_save_count(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "customers.average_monthly_customers", 80, "count")
        entry = self._raw_json("ARKAN")["fields"]["customers"]["average_monthly_customers"]
        self.assertEqual(entry["unit"], "count")

    def test_unit_save_percent(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.gross_margin", 23.5, "percent")
        entry = self._raw_json("ARKAN")["fields"]["finance"]["gross_margin"]
        self.assertEqual(entry["unit"], "percent")


# ---------------------------------------------------------------------------
# 4) previous value / 5) previous unit
# ---------------------------------------------------------------------------


class TestPrevious(BusinessTestCase):
    def test_previous_value_saved_on_update(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 120000000, "UZS")
        entry = self._raw_json("ARKAN")["fields"]["finance"]["revenue"]
        self.assertEqual(entry["value"], 120000000)
        self.assertEqual(entry["previous"]["value"], 100000000)

    def test_previous_unit_saved_on_update(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 120000000, "UZS")
        entry = self._raw_json("ARKAN")["fields"]["finance"]["revenue"]
        self.assertEqual(entry["unit"], "UZS")
        self.assertEqual(entry["previous"]["unit"], "UZS")

    def test_previous_kept_when_unit_changes_only(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "USD")
        entry = self._raw_json("ARKAN")["fields"]["finance"]["revenue"]
        self.assertEqual(entry["unit"], "USD")
        self.assertEqual(entry["previous"]["value"], 100000000)
        self.assertEqual(entry["previous"]["unit"], "UZS")

    def test_no_previous_on_first_write(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        entry = self._raw_json("ARKAN")["fields"]["finance"]["revenue"]
        self.assertNotIn("previous", entry)

    def test_no_new_previous_when_value_unchanged(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 120000000, "UZS")
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 120000000, "UZS")
        entry = self._raw_json("ARKAN")["fields"]["finance"]["revenue"]
        # eskisi (100mln) ele "previous"-te qalıwı kerek, 120mln menen
        # almastırılmawı kerek (qıymat ózgermegen jazba jańa "previous"
        # jasamaydı, eskisin saqlap qaladı)
        self.assertEqual(entry["previous"]["value"], 100000000)


# ---------------------------------------------------------------------------
# 6) update numeric field (jalpı ózgeris ssenariyi)
# ---------------------------------------------------------------------------


class TestUpdateNumericField(BusinessTestCase):
    def test_update_numeric_field_end_to_end(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        path = business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 120000000, "UZS")
        self.assertTrue(path.exists())
        data = business.load_business(self.memory_dir, "ARKAN")
        entry = data["fields"]["finance"]["revenue"]
        self.assertEqual(entry["value"], 120000000)
        self.assertEqual(entry["unit"], "UZS")
        self.assertEqual(entry["previous"]["value"], 100000000)


# ---------------------------------------------------------------------------
# 7) unknown unit (eki jaǵday: berilmegen -> "unknown"; belgisiz -> qátelik)
# ---------------------------------------------------------------------------


class TestUnknownUnit(BusinessTestCase):
    def test_missing_unit_defaults_to_unknown(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000)
        entry = self._raw_json("ARKAN")["fields"]["finance"]["revenue"]
        self.assertEqual(entry["unit"], "unknown")

    def test_empty_string_unit_defaults_to_unknown(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "")
        entry = self._raw_json("ARKAN")["fields"]["finance"]["revenue"]
        self.assertEqual(entry["unit"], "unknown")

    def test_unrecognized_unit_raises(self):
        with self.assertRaises(ValueError):
            business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "som")

    def test_unrecognized_unit_does_not_silently_convert(self):
        # "mln" bir ólshem birligi EMES (multiplier), sonıń ushın qátelik
        # kerek — hesh qashan "UZS" dep ózinen oylap tabılmawı kerek.
        with self.assertRaises(ValueError):
            business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100, "mln")


# ---------------------------------------------------------------------------
# 8) unknown / jaramsız numeric qıymat
# ---------------------------------------------------------------------------


class TestUnknownNumericValue(BusinessTestCase):
    def test_non_numeric_text_raises(self):
        with self.assertRaises(ValueError):
            business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", "100 mln som", "UZS")

    def test_empty_value_raises(self):
        with self.assertRaises(ValueError):
            business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", "", "UZS")

    def test_bool_value_raises(self):
        with self.assertRaises(ValueError):
            business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", True, "UZS")

    def test_nan_value_raises(self):
        with self.assertRaises(ValueError):
            business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", float("nan"), "UZS")

    def test_infinity_value_raises(self):
        with self.assertRaises(ValueError):
            business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", float("inf"), "UZS")

    def test_numeric_field_on_non_numeric_field_key_raises(self):
        # 'products.categories' — scalar maydan, numeric EMES.
        with self.assertRaises(ValueError):
            business.set_numeric_field(self.memory_dir, "ARKAN", "products.categories", 5, "count")

    def test_unknown_field_key_raises(self):
        with self.assertRaises(ValueError):
            business.set_numeric_field(self.memory_dir, "ARKAN", "finance.not_a_real_field", 5, "UZS")

    def test_no_partial_write_on_invalid_value(self):
        # Qátelik bolǵanda fayl da jazılmawı kerek (atomic — jarım-jasar
        # jaǵday joq).
        business_dir = self.memory_dir / "business_data"
        with self.assertRaises(ValueError):
            business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", "belgisiz", "UZS")
        self.assertFalse((business_dir / "arkan.json").exists())


# ---------------------------------------------------------------------------
# 9) bar (eski) SCALAR/tekst maydan ushın regression — set_field() ÓZGERISSIZ
# ---------------------------------------------------------------------------


class TestScalarFieldRegression(BusinessTestCase):
    def test_set_field_still_works_for_plain_scalar_field(self):
        business.set_field(self.memory_dir, "ESTELIK", "products.categories", "granit tas")
        data = business.load_business(self.memory_dir, "ESTELIK")
        self.assertEqual(data["fields"]["products"]["categories"]["value"], "granit tas")

    def test_set_field_still_works_as_plain_text_on_now_numeric_field(self):
        # finance.revenue endi type="numeric", BIRAQ set_field() ele
        # eski tekst jolı menen isleydi (backwards compatible, tools.py
        # osı arqalı jumıs isteydi).
        business.set_field(self.memory_dir, "ARKAN", "finance.revenue", "100 mln som")
        data = business.load_business(self.memory_dir, "ARKAN")
        entry = data["fields"]["finance"]["revenue"]
        self.assertEqual(entry["value"], "100 mln som")
        self.assertNotIn("unit", entry)

    def test_set_field_previous_mechanism_unchanged(self):
        business.set_field(self.memory_dir, "ESTELIK", "goals.current", "Jańa klientler tabıw")
        business.set_field(self.memory_dir, "ESTELIK", "goals.current", "Qarızdan shıǵıw")
        data = business.load_business(self.memory_dir, "ESTELIK")
        entry = data["fields"]["goals"]["current"]
        self.assertEqual(entry["value"], "Qarızdan shıǵıw")
        self.assertEqual(entry["previous"]["value"], "Jańa klientler tabıw")


# ---------------------------------------------------------------------------
# 10) LIST field regression — append_to_list_field TIYILMEGEN
# ---------------------------------------------------------------------------


class TestListFieldRegression(BusinessTestCase):
    def test_append_to_list_field_still_works(self):
        business.append_to_list_field(self.memory_dir, "ARKAN", "products.equipment", "lazer stanogı")
        business.append_to_list_field(self.memory_dir, "ARKAN", "products.equipment", "poroshok boyaw pechkası")
        data = business.load_business(self.memory_dir, "ARKAN")
        items = data["fields"]["products"]["equipment"]["value"]
        self.assertEqual(items, ["lazer stanogı", "poroshok boyaw pechkası"])

    def test_append_to_list_field_dedupes(self):
        business.append_to_list_field(self.memory_dir, "ARKAN", "products.equipment", "lazer stanogı")
        business.append_to_list_field(self.memory_dir, "ARKAN", "products.equipment", "Lazer Stanogı")
        data = business.load_business(self.memory_dir, "ARKAN")
        items = data["fields"]["products"]["equipment"]["value"]
        self.assertEqual(len(items), 1)

    def test_append_to_list_field_rejects_numeric_field(self):
        with self.assertRaises(ValueError):
            business.append_to_list_field(self.memory_dir, "ARKAN", "finance.revenue", "100000000")

    def test_set_numeric_field_rejects_list_field(self):
        with self.assertRaises(ValueError):
            business.set_numeric_field(self.memory_dir, "ARKAN", "products.equipment", 5, "count")


# ---------------------------------------------------------------------------
# 11) valid JSON (hár jazıwda fayl haqıyqıy JSON bolıp qaladı)
# ---------------------------------------------------------------------------


class TestValidJson(BusinessTestCase):
    def test_file_is_valid_json_after_numeric_write(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        path = self.memory_dir / "business_data" / "arkan.json"
        raw = path.read_text(encoding="utf-8")
        # json.loads qátelik bermese — haqıyqıy JSON.
        parsed = json.loads(raw)
        self.assertIn("finance", parsed["fields"])
        # NaN/Infinity JSON-da "nan"/"Infinity" sıyaqlı jaramsız token
        # retinde shıqpawı kerek (Python-nıń json.dumps ony jazıp qoyıp,
        # basqa parserlerde qátelik beredi).
        self.assertNotIn("NaN", raw)
        self.assertNotIn("Infinity", raw)

    def test_file_is_valid_json_after_mixed_writes(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        business.set_field(self.memory_dir, "ARKAN", "products.categories", "temir ónimler")
        business.append_to_list_field(self.memory_dir, "ARKAN", "products.equipment", "lazer stanogı")
        business.add_knowledge_note(self.memory_dir, "ARKAN", "jańa produkt tayarlanıp atır")
        path = self.memory_dir / "business_data" / "arkan.json"
        parsed = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(parsed["business_name"], "ARKAN")


# ---------------------------------------------------------------------------
# 12) restart/read simulation — process qayta baslanǵanday, taza jükleniw
# ---------------------------------------------------------------------------


class TestRestartReadSimulation(BusinessTestCase):
    def test_reread_after_simulated_restart(self):
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.revenue", 100000000, "UZS")
        business.set_numeric_field(self.memory_dir, "ARKAN", "finance.cost", 30000000, "UZS")
        business.set_field(self.memory_dir, "ARKAN", "products.categories", "temir ónimler")
        business.append_to_list_field(self.memory_dir, "ARKAN", "products.equipment", "lazer stanogı")

        # "server qayta iske tústi" sıyaqlı — modul-level kesh joq,
        # load_business() hár safar fayldan tikkeley oqıydı.
        data = business.load_business(self.memory_dir, "ARKAN")

        self.assertEqual(data["fields"]["finance"]["revenue"]["value"], 100000000)
        self.assertEqual(data["fields"]["finance"]["revenue"]["unit"], "UZS")
        self.assertEqual(data["fields"]["finance"]["cost"]["value"], 30000000)
        self.assertEqual(data["fields"]["products"]["categories"]["value"], "temir ónimler")
        self.assertEqual(data["fields"]["products"]["equipment"]["value"], ["lazer stanogı"])


# ---------------------------------------------------------------------------
# Qosımsha: legacy migration regressiyası (numeric-ke aylanǵan maydanlar
# LEGACY_FIELD_ALIASES-ta da bar — average_check, average_monthly_customers)
# ---------------------------------------------------------------------------


class TestLegacyMigrationRegression(BusinessTestCase):
    def _write_raw(self, business_name: str, payload: dict) -> Path:
        d = self.memory_dir / "business_data"
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{business._slugify(business_name)}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def test_legacy_avg_check_migrates_without_unit(self):
        self._write_raw(
            "ARKAN",
            {
                "business_name": "ARKAN",
                "fields": {"customers": {"avg_check": {"value": "350 000 som", "updated_at": "2026-01-01T00:00:00"}}},
                "notes": [],
            },
        )
        data = business.load_business(self.memory_dir, "ARKAN")
        entry = data["fields"]["sales"]["average_check"]
        self.assertEqual(entry["value"], "350 000 som")
        self.assertNotIn("unit", entry)  # eski tekst maǵlıwmatta unit oylap tabılmaydı
        self.assertNotIn("avg_check", data["fields"].get("customers", {}))

    def test_legacy_goals_migration_unaffected_by_unit_change(self):
        # goals.* aliaslar numeric penen baylanıssız — _merge_entry
        # ózgerisi olarǵa tásir etpewi kerek.
        self._write_raw(
            "ESTELIK",
            {
                "business_name": "ESTELIK",
                "fields": {"goals": {"goals_1_year": {"value": "eki filial ashıw", "updated_at": "2026-01-01T00:00:00"}}},
                "notes": [],
            },
        )
        data = business.load_business(self.memory_dir, "ESTELIK")
        entry = data["fields"]["goals"]["one_year"]
        self.assertEqual(entry["value"], "eki filial ashıw")
        self.assertNotIn("unit", entry)


if __name__ == "__main__":
    unittest.main()
