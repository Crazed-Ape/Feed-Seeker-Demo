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
| 3 | The phones' PDF readers | Ruled out | "Download failed" happens before any reader sees the file. The third phone got something that wasn't a working PDF. |
| 4 | The file, or how the site hands it over | Guilty | Same phone, same site, same wifi: v2 works, v3 fails. Only the file differs. |

## The culprit

Side by side, v2 and v3 differ in one place that matters:

| | v2 | v3 |
|---|----|----|
| Size | 11.8 MB | 14.2 MB |
| Described as | PDF document | PDF document |
| Name | `print-and-play-v2.pdf` | `print and play v3.pdf` |

The spaces in v3's name. A web address can't hold a real space. Laptop browsers quietly write it as `%20` and ask for the right file. The testers' phone browsers read the address only up to the first space, ask for a file called `print`, and get the site's "page not found" page. Most report "Download failed". The third phone saved that "not found" page under the PDF's name, which is why it "can't be opened".

The name was typed by hand late at night. I checked the upload only the way a laptop does, so it slipped through for three days. A phone check that night would have caught it.

## Meanwhile

All twelve testers got v3 as an email attachment while the case was open.

## The fix

1. v3 renamed to `print-and-play-v3.pdf`, and the download button pointed at the new name.
2. The upload page cleans every file name: letters, numbers, dots and dashes stay, everything else becomes a dash.
3. Doubled dashes collapse into one.
4. The old address forwards to the new one:
   1. Old: `/files/print-and-play/print and play v3.pdf`
   2. New: `/files/print-and-play/print-and-play-v3.pdf`
5. v2 stays where it was: `/files/print-and-play/print-and-play-v2.pdf`.

The rules live in `upload-rules.json`.

## Review findings ({{c6.name}})

| # | Finding | Level | Done |
|---|---------|-------|------|
| 1 | After the rename, the old address with spaces fails on laptops too; forward it | Must fix | Yes |
| 2 | `#` and `?` break addresses like spaces do; keep only letters, numbers, dots and dashes | Should fix | Yes |
| 3 | Collapse doubled dashes | Optional | Yes |
| 4 | Button says v3, v2 untouched | No action | Checked |

Finding 1 was the important catch: without it, the phones would have been fixed and every saved link on the laptops broken.

## Phone checks ({{c7.name}})

Run on {{p1.name}}'s phone, the old kitchen-drawer phone and the laptop.

| # | Check | Result |
|---|-------|--------|
| 1 | Button on a phone: file opens, 18 pages, event cards on pages 11 to 13 | Passed |
| 2 | Old address with spaces on a phone: lands on the same file | Passed |
| 3 | Steps 1 and 2 on the older phone | Passed |
| 4 | Upload `test file #1.pdf` on the laptop: saved as `test-file-1.pdf` | Passed |
| 5 | Test file deleted and gone from the folder list | Passed |

## Housekeeping

1. The site's deploy token was pasted into a chat during the case. It was replaced and the old one deleted.
2. Next time I ask for settings, I'll ask for everything except the token line.

## Lessons

1. Check every new upload on a phone before it's shared.
2. Every suspect gets a "ruled out, because", never a "probably".

## Log

1. Case opened: facts, four suspects, three pieces of evidence requested.
2. Evidence in: testers' words, a phone in the house, the upload settings. Suspects 1 to 3 ruled out.
3. v2 opens on a phone where v3 fails: the case narrows to v3.
4. Culprit named: the spaces in the file name.
5. Fix built on the test copy, reviewed by {{c6.name}}, three findings fixed, live.
6. Checked by {{c7.name}} on two phones and the laptop: five for five. Case closed.
