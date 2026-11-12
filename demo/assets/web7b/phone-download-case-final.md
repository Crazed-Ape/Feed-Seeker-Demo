# Case: the print-and-play won't download on phones

Case notes kept by {{c5.name}}. Closed.

## The complaint

Three of the twelve playtesters said the {{pick.game}} print-and-play download failed on their phones, days before Friday's playtest. Laptops were never affected.

## Facts

1. v3 went up through the upload page three days before the reports: 14.2 MB, 18 pages, event cards on pages 11 to 13.
2. It downloaded and opened on a laptop, the night it went up and again when the reports came in.
3. v2 (11.8 MB, 16 pages) sat on the site for five weeks, was downloaded about 140 times, and nobody reported a problem.
4. Two testers and {{p1.name}}'s phone: a spinner for about a second, then "Download failed".
5. The third tester: the file downloaded but "can't be opened".
6. Upload settings: folder `/files/print-and-play`, limit 50 MB, allowed pdf, png and zip.
7. v2, opened from its old address on the same phones where v3 failed, downloaded and opened straight away.

## Suspects

| # | Suspect | Verdict | Because |
|---|---------|---------|---------|
| 1 | The file is too big for phones | Ruled out | A size problem fails late, after a long spinner; these failed within a second. The upload limit is 50 MB. |
| 2 | The phone layout breaks the button | Ruled out | The tap lands; the spinner and the banner prove it. |
| 3 | The phones' PDF readers | Ruled out | "Download failed" happens before any reader sees the file. The third phone saved the file but didn't know what it was. |
| 4 | The file, or how the site hands it over | Guilty | Same phone, same site, same wifi: v2 works, v3 fails. The file itself is fine on laptops, so it's how the site sends it. |

## The culprit

Side by side, v2 and v3 differ in one place that matters:

| | v2 | v3 |
|---|----|----|
| Size | 11.8 MB | 14.2 MB |
| Name | `print-and-play-v2.pdf` | `print-and-play-v3.pdf` |
| Described as | PDF document | unknown binary data |

The label. Every file the site sends comes with a label that tells the browser what it is. v2 was uploaded the old way, which set the label. v3 went through the drag-and-drop upload page I built last month, and that page never set one, so the site fell back to "unknown binary data".

A laptop browser sees ".pdf" at the end of the name, ignores the label and opens the file. Phones trust the label. Some refuse a file they can't identify, which is the "Download failed". The third phone saved the file but didn't know it was a PDF, so it offered nothing to open it with.

This one was my bug, not the upload. A phone check of the new page when I built it would have caught it.

## Meanwhile

All twelve testers got v3 as an email attachment while the case was open.

## Other files

Three files went through the new upload page this month:

| File | Label before | Now |
|---|---|---|
| v3 print-and-play | unknown binary data | PDF document |
| Press kit zip | unknown binary data | ZIP archive |
| Card preview pictures | picture (phones recognize these without help) | unchanged |

## The fix

1. v3 and the press kit zip relabeled.
2. The upload page sets each file's label from its ending: pdf, png and zip.
3. The upload page refuses a file whose ending it can't label, and says in plain words which ending it doesn't know.
4. Files in the downloads folder are kept for ten minutes instead of a day, so phones that stored the badly labeled copy ask again on their next try.

The settings live in `download-settings.json`.

## Review findings ({{c6.name}})

| # | Finding | Level | Done |
|---|---------|-------|------|
| 1 | Phones that already failed may reuse the stored bad copy for a day | Must fix | Yes, by the ten-minute keep time instead of a new button address |
| 2 | Refuse endings the page can't label | Should fix | Yes |
| 3 | Check the press kit zip on a phone, not only the PDF | For {{c7.name}} | Yes |
| 4 | v3 itself is unchanged | No action | Checked |

Finding 1 was the important catch. A new button address would have fixed the button but not the v3 links testers had already passed around; the shorter keep time fixes both.

## Phone checks ({{c7.name}})

Run on {{p1.name}}'s phone, the old kitchen-drawer phone and the laptop.

| # | Check | Result |
|---|-------|--------|
| 1 | Button on a phone: file opens, 18 pages, event cards on pages 11 to 13 | Passed |
| 2 | Press kit link on a phone: offers to open or save a zip | Passed |
| 3 | Steps 1 and 2 on the older phone | Passed |
| 4 | A small test PDF uploaded on the laptop opens on a phone | Passed |
| 5 | Test file deleted and gone from the folder list | Passed |

With the ten-minute keep time, any phone that stored the badly labeled copy gets the right file on its next try.

## Housekeeping

1. The site's deploy token was pasted into a chat during the case. It was replaced and the old one deleted.
2. Next time I ask for settings, I'll ask for everything except the token line.

## Lessons

1. Check every new upload on a phone before it's shared.
2. Check a new tool of mine on a phone before anyone else uses it.
3. Every suspect gets a "ruled out, because", never a "probably".

## Log

1. Case opened: facts, four suspects, three pieces of evidence requested.
2. Evidence in: testers' words, a phone in the house, the upload settings. Suspects 1 to 3 ruled out.
3. v2 opens on the phones where v3 fails: the case narrows to v3.
4. Culprit named: the missing label from the new upload page.
5. Fix built on the test copy, reviewed by {{c6.name}}, live with one finding solved a different way.
6. Checked by {{c7.name}} on two phones and the laptop: five for five. Case closed.
