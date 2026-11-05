# Moodumi website

A responsive, buildless English website for Moodumi: Home, Privacy Policy, and Support. It uses HTML, shared CSS, a small local script for optional screenshot navigation, and website-owned copies of the approved app artwork and real app captures.

The app is **coming soon on iPhone and iPad**. The website is prepared for local review; this work does not publish GitHub Pages, commit, or push files automatically.

## Preview locally

Python 3.9 or newer is the only requirement for the local preview and validator. There are no packages to install, build steps, external fonts, analytics services, or visitor-side runtime dependencies.

```sh
cd /Users/minh/Documents/Projects/alex-duyminhtran.github.io
python3 scripts/preview.py
```

Open **http://127.0.0.1:8765/**. The preview serves the website at the root, matching this GitHub Pages user repository. Use `--port 8766` to choose another local port. Stop with Ctrl+C.

The server binds only to `127.0.0.1`, does not list directories, and does not serve hidden files, repository metadata, source scripts, or parent folders. It is a local review tool, not a production server.

## Validate

```sh
python3 scripts/validate-site.py
python3 scripts/validate-site.py --report verification/site-validation.json
```

The standard-library validator checks HTML structure, page metadata, unique IDs and skip links, shared navigation, root-site link and asset resolution, email links, image dimensions, asset provenance hashes, and the absence of placeholder App Store links, forms, external fonts, and third-party scripts. It reports errors with file locations and exits unsuccessfully when an error is found. It does not replace visual or assistive-technology testing.

For visual review, inspect all three pages at phone, tablet, and desktop widths, including 200% browser zoom, keyboard navigation, and reduced motion. Check the Home screenshot gallery with and without JavaScript. Privacy and Support use ordinary HTML and remain readable without JavaScript. Local preview captures and validation reports belong in the ignored `verification/` directory.

### Original website checks completed on 5 November 2026

- All three pages inspected in the local in-app browser at 390, 768, and 1440 CSS pixels, with every displayed asset loaded and no page-level horizontal overflow. Additional 320- and 720-pixel reflow checks passed.
- Manual gallery controls reached both ends on the phone layout. Skip navigation moved keyboard focus to the main content with a visible focus indicator; Privacy navigation, contents links, and native Support FAQ expansion worked.
- Privacy and Support contain no JavaScript. Their text, navigation, and FAQs are ordinary HTML. The Home gallery remains a native scroll region when its optional control script is absent.
- The validator passed for three pages, 74 website references, and 24 approved assets. HTTP checks passed for 47 route/asset cases, 15 anchors, and 17 denied private or traversal paths.
- Twenty-five text/background palette pairs meet at least 4.5:1 contrast. Gallery logic checks passed with both reduced-motion preferences and both scroll boundaries.
- Original artwork/source captures remain unchanged. Original full-page and viewport previews and machine-readable reports are preserved in `verification/source-website/`. These describe the source website before the root-URL migration; migration checks are recorded separately in `verification/`.

**Remaining manual checks:** the available preview controls did not expose native 200% browser zoom or actual operating-system Reduce Motion preference changes. The 720-pixel layout checks represent the reflow width of a 1440-pixel browser at 200% zoom; they do not claim that browser zoom itself was changed. Static artwork has no animation, and the gallery's motion preference handling was checked in isolation. A full screen-reader session and physical-device/browser checks have not been performed.

## Publish later with GitHub Pages

The intended repository is `https://github.com/alex-duyminhtran/alex-duyminhtran.github.io`. After reviewing the website, commit and push these files to that repository's `main` branch. No publishing is performed by the local scripts.

GitHub Free provides Pages for public repositories. Keep this website repository separate from the iOS app source; publishing these website files does not require making the app repository public.

1. Open the repository on GitHub and choose **Settings → Pages**.
2. Under **Build and deployment**, choose **Deploy from a branch**.
3. Choose **main** and **/(root)**, then save.
4. Wait for GitHub's Pages deployment to complete. Open the published site in a private browser window and check all three pages and images.

The expected URLs after successful publication are:

- Home: `https://alex-duyminhtran.github.io/`
- Privacy Policy: `https://alex-duyminhtran.github.io/privacy.html`
- Support: `https://alex-duyminhtran.github.io/support.html`

These are intended URLs, not a claim that the site is already live. `.nojekyll` keeps the checked-in static files on the plain GitHub Pages path. All site navigation and local assets use relative URLs. Canonical and social-preview URLs point to the root of `alex-duyminhtran.github.io`.

Once live, the Privacy Policy and Support URLs can be entered in App Store Connect. Adding an accessible link to the published privacy policy inside the iOS app is a separate follow-up.

## Repository migration

The website was copied from the sibling `MoodumiWebsite` folder. Its artwork, CSS, app captures, and gallery behavior are unchanged. The new repository retains its own Git history and remote; the source repository remains untouched. Migration checks passed for all three pages, 74 website references, 24 approved assets, and 86 GET/HEAD route checks. The root URL serves Home directly without a redirect loop. A desktop browser check confirmed root canonical URLs, loaded images, and no horizontal overflow on Home, Privacy, and Support. All original asset bytes and the destination Git history and remote are preserved. Current reports and the root-site preview capture are in `verification/`.

## Content and updates

- Developer: **Minh Tran**
- Public support and privacy email: **alex.duyminhtran@gmail.com**
- Main pages: `index.html`, `privacy.html`, and `support.html`
- Shared presentation: `styles.css` and `scripts/site.js`
- Approved artwork and native app captures: `assets/`; its provenance manifest records source and generated-file hashes.

The supplied assets are ready to use. Regenerating them is optional and requires Pillow as a development tool plus the sibling Moodumi source folder:

```sh
python3 scripts/prepare-assets.py --source-root ../Moodumi
```

The generator makes byte-identical PNG copies and proportional WebP renditions of the approved artwork and app captures. It also prepares favicons and the social image. It does not modify the Moodumi app or its source artwork.

When Moodumi is available on the App Store, replace the Coming soon message with the verified app link. Do not invent an App Store URL or a download button before the listing is available. Update the social metadata if the public site address changes.

The Privacy Policy describes the present app: local journal and Growth records, on-device calculations, no account, and no app advertising or analytics services. Apple-controlled device backups and transfers can include local data. Support email and GitHub Pages hosting are described separately; GitHub logs visitors' IP addresses for security. The developer cannot retrieve records held only on a user's device.

Review the policy and its date when storage, app services, website hosting, or support practices change. Do not add analytics, fonts from a third party, external widgets, forms, or other services without first reviewing and updating the policy.
