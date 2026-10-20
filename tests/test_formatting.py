from django.test import SimpleTestCase, override_settings

from apps.telegram_bot.formatting import html_to_telegram, truncate_telegram, visible_length


@override_settings(SITE_URL="https://welicodev.uz")
class TelegramFormattingTests(SimpleTestCase):
    def test_rich_text_conversion(self):
        out = html_to_telegram(
            '<h2>Sarlavha</h2><p><strong>Qalin</strong> &amp; <em>kursiv</em> <a href="/uz/blog/">blog</a></p>'
            '<ul><li>bir</li><li>ikki</li></ul><pre><code class="language-bash">echo "&lt;x&gt;"</code></pre>'
            '<blockquote><p>Iqtibos</p></blockquote><figure><img src="a.png"></figure><table><tr><td>j</td></tr></table>'
        )
        self.assertIn("<b>Sarlavha</b>", out)
        self.assertIn("<b>Qalin</b> &amp; <i>kursiv</i>", out)
        self.assertIn('<a href="https://welicodev.uz/uz/blog/">blog</a>', out)
        self.assertIn("• bir\n• ikki", out)
        self.assertIn('<pre><code class="language-bash">echo "&lt;x&gt;"</code></pre>', out)
        self.assertIn("<blockquote>Iqtibos</blockquote>", out)
        self.assertNotIn("<img", out)
        self.assertNotIn("<p>", out)

    def test_script_and_unknown_tags_removed(self):
        out = html_to_telegram('<p>ok<script>alert(1)</script><span style="x">matn</span></p>')
        self.assertEqual(out, "okmatn")

    def test_truncate_keeps_tags_balanced(self):
        html = "\n\n".join(f"<b>Blok {i}</b> " + "so'z " * 30 for i in range(20))
        cut = truncate_telegram(html, 300)
        self.assertLessEqual(visible_length(cut), 300)
        self.assertEqual(cut.count("<b>"), cut.count("</b>"))
        self.assertTrue(cut.endswith("…"))
