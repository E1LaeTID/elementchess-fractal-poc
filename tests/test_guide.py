import unittest

from elementchess.guide import GUIDE_PAGES, GuideBook


class GuideBookTest(unittest.TestCase):
    def test_notice_contains_player_rules_only(self) -> None:
        self.assertEqual(len(GUIDE_PAGES), 8)
        self.assertTrue(any(page.chapter == "V" for page in GUIDE_PAGES))

    def test_section_four_is_a_single_page(self) -> None:
        section_four = [page for page in GUIDE_PAGES if page.chapter.startswith("IV")]
        self.assertEqual(len(section_four), 1)
        self.assertEqual(section_four[0].chapter, "IV")

    def test_section_four_only_contains_player_facing_wheel_rules(self) -> None:
        section_four = next(page for page in GUIDE_PAGES if page.chapter == "IV")
        self.assertIn("Chaque jeton que vous placez", section_four.body)
        self.assertIn("son orientation compte également", section_four.body)
        self.assertIn("À LA FIN DE LA RONDE", section_four.body)
        self.assertIn("l'annonce de la suivante", section_four.body)
        self.assertIn("relativement à la destination de chaque camp", section_four.body)
        self.assertNotIn("VALEUR_TERRAIN × COEFFICIENT_LIGNE", section_four.body)

    def test_navigation_is_clamped_to_existing_pages(self) -> None:
        guide = GuideBook()
        guide.previous()
        self.assertEqual(guide.index, 0)
        for _ in range(len(guide.pages) + 3):
            guide.next()
        self.assertEqual(guide.index, len(guide.pages) - 1)

    def test_technical_wheel_content_is_absent_from_player_guide(self) -> None:
        guide_text = "\n".join(page.body for page in GUIDE_PAGES)
        self.assertNotIn("wheel_game", guide_text)
        self.assertNotIn("wheel_thunder", guide_text)
        self.assertNotIn("Δ_e(t)", guide_text)


if __name__ == "__main__":
    unittest.main()
