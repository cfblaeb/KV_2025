import re
import scrapy
from w3lib.html import get_base_url
from .extracter import extract_next_f_json
import extruct
from pathlib import Path


class DRSpider(scrapy.Spider):
    name = 'DR'
    allowed_domains = ['dr.dk']
    start_urls = ['https://www.dr.dk/nyheder/politik/kommunalvalg/din-stemmeseddel']

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                meta={"playwright": True, "playwright_include_page": True}
            )

    async def parse(self, response):
        #print("her er første parser")
        page = response.meta["playwright_page"]
        kredse_urls = await page.query_selector_all("a[aria-label*='gå til stemmeseddel']")
        #kredse_urls = response.css("a[aria-label*='gå til stemmeseddel']")
        #print(kredse_urls)
        for urls in kredse_urls:
            href = await urls.get_attribute('href')
            if not href:
                continue
            # response.follow will correctly join relative URLs to the base URL
            yield response.follow(href, callback=self.parse_kreds, meta={"playwright": True, "playwright_include_page": True})
            #break
        await page.close()

    async def parse_kreds(self, response):
        page = response.meta["playwright_page"]
        #kandidat_urls = response.css("a[aria-label*='gå til kandidatprofil']")
        kandidat_urls = await page.query_selector_all("a[aria-label*='gå til stemmeseddel']")
        
        for urls in kandidat_urls:
            href = await urls.get_attribute('href')
            if not href:
                continue
            yield response.follow(href, callback=self.parse_kandidat)
            #yield scrapy.Request(response.urljoin(href), callback=self.parse_kandidat, meta={"playwright": True, "playwright_include_page": True})
            #break        
        await page.close()

    def parse_kandidat(self, response):
        base_url = get_base_url(response.text, response.url)
        data = extruct.extract(response.text, base_url=base_url)
        text_blocks = response.css("script::text").getall()
        for block in text_blocks:
            if "candidateAnswers" in block:
                # det er den her
                try:
                    data = extract_next_f_json(block)[0][3]['children'][3]
                    yield data
                except Exception as e:
                    print(f"hmm nej: {e}")
