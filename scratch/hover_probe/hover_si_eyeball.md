# HoVer SI extended eyeball — actionability vs page-difficulty

40 HoVer 3-hop claims (threehop[10:50]) through the DSPy multi-hop program (gpt-4.1-mini, BM25 over 5.23M wiki abstracts). Actionability features are pure title-structure ($0, no LLM).

## ~10 verbatim SI strings (spread across recall)

- recall=0.00 | **SI:** Correctly retrieved 0/3 gold documents: []. Documents remaining to be retrieved: ['David Zayas', 'John Malkovich', 'Rounders (film)'].
- recall=0.00 | **SI:** Correctly retrieved 0/3 gold documents: []. Documents remaining to be retrieved: ['Philemon (musical)', 'The Fantasticks (film)', 'Tom Jones (writer)'].
- recall=0.00 | **SI:** Correctly retrieved 0/3 gold documents: []. Documents remaining to be retrieved: ['2012 Open Sud de France – Doubles', 'Heather Watson', 'Édouard Roger-Vasselin'].
- recall=0.00 | **SI:** Correctly retrieved 0/3 gold documents: []. Documents remaining to be retrieved: ['Nancy R. Howell', 'Saint Paul School of Theology', 'United Methodist Church of the Resurrection'].
- recall=0.67 | **SI:** Correctly retrieved 2/3 gold documents: ['Art of Life 1993.12.31 Tokyo Dome', 'Warrel Dane']. Documents remaining to be retrieved: ['Toshi (musician)'].
- recall=0.67 | **SI:** Correctly retrieved 2/3 gold documents: ['Mike Smith (A&amp;R man)', 'Quietdrive']. Documents remaining to be retrieved: ['Supergrass'].
- recall=0.67 | **SI:** Correctly retrieved 2/3 gold documents: ['2009 Manitoba Scotties Tournament of Hearts', 'Jennifer Jones (curler)']. Documents remaining to be retrieved: ['2007 Trail Appliances Autumn Gold Curling Classic'].
- recall=1.00 | **SI:** Correctly retrieved 3/3 gold documents: ['Battle of Harlem Heights', 'Battle of White Plains', 'New York and New Jersey campaign']. Documents remaining to be retrieved: [].
- recall=1.00 | **SI:** Correctly retrieved 3/3 gold documents: ["Holiday World &amp; Splashin' Safari", 'The Voyage (roller coaster)', 'Wooden roller coaster']. Documents remaining to be retrieved: [].
- recall=1.00 | **SI:** Correctly retrieved 3/3 gold documents: ['Chas Chandler (comics)', 'Hellblazer Special: Bad Blood', 'John Constantine']. Documents remaining to be retrieved: [].

## Page-type histogram of ALL missed gold docs (Part 2c — the key check)

- total missed docs: **38**  |  PLAIN (no structural marker): **28** (74%)  |  structured: **10** (26%)
  - PLAIN: 28
  - WORK: 7
  - PERSON: 2
  - PLACE: 1

## Actionability × difficulty cross-tab (Part 2d)

Missed docs, `structured page-type (≠PLAIN)` × miss-depth of the claim (deep = the claim missed ≥2 of 3 gold docs; near = missed exactly 1):

| | deep-miss (≥2 missed) | near-miss (1 missed) |
|---|---|---|
| **structured** | 7 | 3 |
| **PLAIN** | 20 | 8 |

Mean obscurity (log10 corpus-rarity of title tokens): **missed 3.43** vs **retrieved-gold 3.39** (higher = rarer).

## Full 40-claim feature table

| claim | recall | n_rem | missed page-types | disambig | mean_obsc |
|---|---|---|---|---|---|
| The film The Book Thief, released in 1990, was | 1.00 | 0 | — |  | 0.0 |
| The president of South Korea was born 24 Janua | 0.33 | 2 | PLAIN,PLAIN |  | 2.98 |
| The writer of the song Girl Talk and song-writ | 0.67 | 1 | PLAIN |  | 4.57 |
| The North Central town that licenses WCJB-TV i | 0.67 | 1 | PLACE |  | 3.02 |
| The movie. in which David Zayas played Francis | 0.00 | 3 | PLAIN,PLAIN,WORK | Y | 3.22 |
| The 2005 black comedy sequel to "Forgetting Sa | 1.00 | 0 | — |  | 0.0 |
| The film Christopher Robin has fewer writers t | 1.00 | 0 | — |  | 0.0 |
| Camp Half-Blood Chronicles is the name of the  | 1.00 | 0 | — |  | 0.0 |
| An American lyricist, born in 1928, co-wrote t | 0.00 | 3 | WORK,WORK,PERSON | Y | 3.06 |
| 1: Parnassius nordmanni is a high altitude but | 1.00 | 0 | — |  | 0.0 |
| The plant commonly affected by  Rhodococcus fa | 0.33 | 2 | PLAIN,PLAIN |  | 5.11 |
| Unchained Memories was the film made before fi | 1.00 | 0 | — |  | 0.0 |
| The director of this 2011 drama that was adapt | 0.33 | 2 | PLAIN,PLAIN |  | 3.25 |
| Farmers' Alliance was the organized agrarian e | 1.00 | 0 | — |  | 0.0 |
| Liberal Arts school Emory University was found | 1.00 | 0 | — |  | 0.0 |
| He was born in a city whose population at the  | 1.00 | 0 | — |  | 0.0 |
| Composer Franz Schreker was also a teacher but | 0.67 | 1 | PLAIN |  | 2.81 |
| In the 2009 the Major League Soccer All-Star G | 1.00 | 0 | — |  | 0.0 |
| This tennis player won a Grand Slam doubles ch | 0.00 | 3 | PLAIN,PLAIN,PLAIN |  | 3.18 |
| The TV series Soul Mates starred Christian Van | 0.67 | 1 | PLAIN |  | 4.05 |
| Piestewa Parkway is  named after a Native Amer | 1.00 | 0 | — |  | 0.0 |
| The actor, who co-stars with  Nitin Sahrawat i | 0.67 | 1 | PLAIN |  | 5.72 |
| The three best sellers from the author of Dete | 0.33 | 2 | PLAIN,WORK | Y | 3.05 |
| The Republican Chairman  born June 1, 1956, wa | 1.00 | 0 | — |  | 0.0 |
| Greek Fire originated in 1998 in a more southe | 0.67 | 1 | WORK | Y | 2.06 |
| The writer and director of this film is Filipi | 0.33 | 2 | PLAIN,WORK | Y | 3.16 |
| The publisher and film company Marvel produced | 0.33 | 2 | PLAIN,PLAIN |  | 3.61 |
| The area where the Changle River originates wa | 0.67 | 1 | PLAIN |  | 5.82 |
| The Blueprint is the name of an outtakes album | 1.00 | 0 | — |  | 0.0 |
| The city of the college that Nancy R. Howell i | 0.00 | 3 | PLAIN,PLAIN,PLAIN |  | 2.73 |
| A Pottawatomie massacre event known was Bleedi | 1.00 | 0 | — |  | 0.0 |
| In the year 2016, the team that a soccer playe | 1.00 | 0 | — |  | 0.0 |
| The campaign, during which the Battle of Harle | 1.00 | 0 | — |  | 0.0 |
| Michael Akerfeldt and the Sonic Youth bandmate | 0.67 | 1 | PLAIN |  | 4.68 |
| An American rock band released My Animal in th | 0.00 | 3 | PLAIN,PLAIN,WORK | Y | 2.59 |
| The musican, whose vocals on the Art of Life 1 | 0.67 | 1 | PERSON | Y | 3.36 |
| A wooden oak roller coaster at Holiday World i | 1.00 | 0 | — |  | 0.0 |
| This character as featured in the comic book,  | 1.00 | 0 | — |  | 0.0 |
| Quietdrive and this group are both rock bands. | 0.67 | 1 | PLAIN |  | 4.87 |
| The athlete, a qualifier for the 2009 Manitoba | 0.67 | 1 | PLAIN |  | 2.84 |

## 5-line HONEST verdict (literal)

1. **Cluster into rule-able page-types?** 10/38 (26%) missed docs have a structural marker; 28 (74%) are PLAIN bare names. Mostly PLAIN one-offs → weak rule-able structure.
2. **Independent of difficulty?** structured misses in NEAR-miss (1-missed) claims = 3 (vs 7 in deep-miss). Structure appears off the deep-miss tail → not purely difficulty.
3. **Obscurity collision:** missed-gold obscurity 3.43 vs retrieved-gold 3.39 (Δ=+0.04). Misses are NOT much rarer → obscurity alone doesn't explain misses.
4. **Actual spend:** $0.1891 (cap $2.0).
5. **Go/no-go lean (not a decision):** LEAN NO-GO — missed-doc actionability looks mostly like page-difficulty/obscurity with little title-structure a scorer could exploit beyond difficulty; the cheap null is not refuted.
