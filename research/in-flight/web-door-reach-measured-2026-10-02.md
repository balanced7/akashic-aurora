# What the web door can and cannot reach, measured 2026-10-02

**Run by claude (Vandor)** at Daniel's ask: "play with the webfetch tools via ask to research
something so we can make sure they work ... I want [the deepseek seat] to be able to actually
research the lore behind elmesia", and "The Fandom is wrong though ... How can we help [him] search
actual source material?"

Every line below is a live result from this morning, not a reading of the code.

## The headline, for whoever picks this up

**Fetch works and reaches the PRIMARY source. Search works and ranks the WRONG sources first, and
the lever that fixes that is the query's LANGUAGE, not the tool.**

## Backend by backend, measured

| path | state | evidence |
|---|---|---|
| `py agent_cli.py web fetch <url>` | WORKS | example.com 200, 713 B; syosetu novel index 200, 81 KB |
| `py agent_cli.py web search` | **WALLED** | "search walled: ddg-lite returned no result markup (bot interstitial). Configure .secrets/brave_api.key" |
| `scripts/local/websearch.py` (SearXNG, the deepseek toolbox's backend) | WORKS, degraded honestly | returns results and prints "[partial: 5 engine(s) refused -- brave too many requests, dictzone access denied, duckduckgo CAPTCHA, startpage CAPTCHA, yep access denied]" |
| `akashic-searxng` container | UP | `docker ps` |
| toolbox `web_fetch` | PRESENT | core/comm/toolbox.py:233 and :1827 |

So there is no missing capability. `web_fetch` is on the toolbox surface, which closes the gap the
2026-07 lesson `web_door_topology_three_backends` warned about ("a seat with no web_fetch tool in
its surface will silently read 'webfetch' as 'the search tool'"). What is missing is a Brave key:
five of roughly ten SearXNG engines refused, and one of them refused *because* it is unkeyed.

## The finding that actually answers the question: query language decides source quality

Same character, two queries, one search backend, minutes apart.

**English — "Tensura Elmesia El-Ru Sarion":**
1. tensura.fandom.com (the wiki Daniel says is wrong)
2. myanimelist.net
3. reddit.com
4. tensura.fandom.com again
5. a Facebook page for an animal clinic in El Paso, in Czech

**Japanese — "エルメシア・エル・リュ・サリオン 転生したらスライムだった件":**
1. dic.pixiv.net encyclopedia entry
2. **www.ten-sura.com/character/elmesia — the OFFICIAL portal**, with her official quote and her
   credited voice actor
3. an unrelated events site

The English query never surfaces an official source. The Japanese query surfaces it second. For a
Japanese work, searching in English is searching the fandom layer; searching in Japanese reaches
the publisher. That is the single cheapest change available and it costs nothing.

## What is reachable, in priority order

**1. The author's own web novel — the actual primary source. VERIFIED WORKING.**
`https://ncode.syosetu.com/n6316bn/` is Fuse's 転生したらスライムだった件 on Shōsetsuka ni Narō.

- index: 200, 81,332 bytes
- chapter 1 at `/n6316bn/1/`: 200, 45,937 bytes, **3,686 characters of clean readable novel text**
- chapters are addressable by number, so research is "fetch `/n6316bn/<N>/` and read"

This beats every wiki by construction. It is the text, by the author, with no intermediary.

**2. Fandom.** Fetches fine. It is what English search ranks first and what Daniel says is wrong.
Usable as a pointer to chapter numbers, never as the claim.

## What is NOT reachable, and why

**The official portal is JavaScript-rendered.** `ten-sura.com/character/elmesia` returns 200 and
122,552 bytes, and the character content is *not in those bytes*. Probed the raw plane for
エルメシア, 金元寿子, 魔導王朝サリオン, 天帝 and 朕: all absent. The HTML is a shell; the content
arrives client-side.

The search snippet showed that content because the upstream engine renders JavaScript and we do
not. So a snippet can be richer than a fetch of the same URL, which is a trap worth naming: do not
conclude a page "has" text because a search result quoted it.

I then tried a real browser on it, which should have worked, and the renderer stalled: the tab
loaded with the correct title but `get_page_text` timed out at 30 s and an injected one-line text
extraction timed out at 45 s. Heavy animation, most likely. **Unresolved, and recorded as
unresolved rather than worked around.**

**pixiv dictionary and Yen Press both refused the fetch outright** (`ok: false`, no status).

## What this means for the Elmesia question specifically

Stated carefully, because the point is to reach sources and not to adjudicate the canon.

From the OFFICIAL portal's own search snippet (ten-sura.com, not a wiki): she is the 天帝 of the
魔導王朝サリオン, her credited voice actor is 金元寿子 (Hisako Kanemoto), and her official pull
quote is 「小僧共が何を考えようが、朕に仇を為せる訳もなし」.

**A specific, checkable hypothesis about where "androgynous" comes from:** that quote uses 朕, the
archaic imperial first person. It is the pronoun of a sovereign, not of a gender, and it is exactly
the sort of thing an English-language wiki summarises as androgynous or ambiguous. If that is the
root, then the error is a translation artifact of a register choice, and the fix is reading the
Japanese rather than arguing with the wiki. **Hypothesis, not a finding.** Settling it means
reading the novel chapters where she appears, which path 1 above makes possible.

## Recommended, in order of value per effort

1. **Search in Japanese for Japanese works.** Free, immediate, and it moved the official source
   from absent to rank 2.
2. **Get a Brave free-tier key into `.secrets/brave_api.key`.** Daniel's to obtain. It un-walls
   `py agent_cli.py web search` entirely and restores one of the five refused SearXNG engines.
3. **Treat `ncode.syosetu.com/n6316bn/<N>/` as the citable source** for this work, with the wiki
   demoted to an index for finding chapter numbers.
4. **Leave the JS-rendered-page problem open.** It needs a rendering fetch path, and the browser
   attempt stalled on this particular site. Do not paper over it; a fetch that returns 200 and a
   shell is a false success, and that is the same family as the `find` verb's false "nothing
   found" fixed this morning.
