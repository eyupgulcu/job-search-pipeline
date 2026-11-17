# ATS-safe CV rules

Applicant tracking systems parse the text layer of the PDF. If the text layer is wrong, the human reader
never sees the CV.

## Layout

- One column. No tables or text boxes for layout. No text inside images. No icon fonts.
- One page for early-career candidates. Two only when there is real, relevant depth.
- Standard headings: Summary, Skills, Experience, Education, Languages. Fancy headings ("My journey")
  confuse section detection.
- Contact line as plain text: email, phone, city, then links. Write links as visible text too, not only as
  link labels.
- Dates as `Mon YYYY - Mon YYYY`. Same format everywhere.
- Fonts: embedded system fonts. Avoid ligature-heavy fonts; a ligature can turn "fi" into one glyph that
  extracts as garbage. The check fails on U+FB01 and U+FB02.

## Tailoring to a posting

1. Read the posting. List its hard requirements, tools, and verbs.
2. Rewrite the summary in two or three sentences using the posting's own role words where the facts allow.
3. Reorder skills and bullets so the matching ones come first.
4. Run `ats_check.py --keywords posting.txt CV-X.pdf` and read the missing-terms list.
5. For each missing term, ask: is it true and in `facts.md`? Yes: add it where it fits. No: leave it out. A
   keyword you cannot defend in an interview costs more than it earns.

## Claim audit

Before building, read the CV and the cover note sentence by sentence. Each claim needs a matching line in
`facts.md`. Typical made-up-claim traps:

- Inflated years of experience or seniority words.
- A tool listed as strong that was used once.
- Metrics with no source ("improved performance by 40%").
- A job title the employer never used.
- Results from a team project written as solo work.

Delete anything without a source. Put terms the candidate must never claim in the `## Forbidden` section so
the script enforces it.

## What `ats_check.py` verifies

One page; a text layer of at least `min_chars` characters; every `required` string present (contact items);
every `headings` entry present; no forbidden term; no broken characters or ligatures; at least `min_links`
clickable link annotations; and, when building, that the PDF file is newer than before the build.

## Non-English characters

Check that language-specific letters survive extraction. For Turkish: İ, ı, ş, ğ, ç, ö, ü. Extract the text
and search for the exact name and city strings as they should appear. Case conversion is a common bug:
without a Turkish locale, `upper()` or CSS `text-transform: uppercase` turns `i` into `I` instead of `İ`,
so type such text in its final case instead of transforming it.

## Upload hygiene

Upload the PDF the check just passed, not an older one with a similar name. Name files
`Firstname-Lastname-Role.pdf`. Keep the posting text archived next to the CV variant that was sent.
