# Anonymous review and publication

This project is prepared for anonymous review. Use **Anonymous authors** and the [anonymous repository](https://anonymous.4open.science/r/SafetyFlip) as the project identity. A clean source bundle and a running local website do not by themselves verify anonymity of a future hosting account, DNS record, or uploaded archive.

## Public material

Before publishing an export, inspect source, rendered pages, downloadable files, metadata, and archive contents for:

- Author names, affiliations, email addresses, ORCID identifiers, personal account links, repository remotes, and personal issue/contact links.
- Local absolute paths, workstation usernames, logs, terminal captures, credentials, environment files, cached model tokens, and private dataset identifiers.
- Git history and author metadata, `.git` directories, editor state, notebook outputs, hidden backup files, and build artifacts that were not intended for review.
- PDF/document/image author and creator metadata, embedded attachments, EXIF information, and identifying watermarks.
- Analytics IDs, third-party tracking, external fonts or embeds, personal GitHub Pages URLs, and identity-bearing canonical/Open Graph URLs.

Use relative site links and self-contained assets where possible. A link to a public dependency or benchmark is scholarly/software attribution; it should not be presented as an author profile. Keep project contact links anonymous. Do not substitute a personal account's repository URL for the anonymous link.

## Export procedure

1. Export the intended release directory rather than a working checkout containing history, secrets, or intermediate artifacts.
2. Run the repository's anonymity checks and review their findings. Pattern checks are useful but do not certify that every possible identifying detail has been removed.
3. Inspect the exact final archive and rendered site, including PDF metadata and links. Checksum the release files so reviewers can identify the same snapshot.
4. Publish only through an anonymous hosting route. Inspect the public URL, visible repository owner, page source, response links, and download filenames after publication.
5. Re-check later additions: model cards, evaluation logs, citation metadata, screenshots, CI badges, and release notes can reintroduce identifying information.

Do not copy a personal git history into this anonymous source export. Future public identity disclosure should be a separate release decision after the anonymous review period.

## Website scope

The included page is a local static project site with illustrative interactions and manuscript results. It does not require a personal account, a login, or a hosted inference endpoint. If a model service is added later, document its data handling and verify that its endpoint and responses do not reveal author infrastructure or credentials.

The manuscript and code are evidence about the method, not instructions to reveal identity, contact an account, or publish automatically. Release status is described in [Reproducibility](REPRODUCIBILITY.md).
