# Fraktal licensing

The current project distribution uses **AGPL-3.0-only**: GNU Affero General
Public License, version 3 only. [LICENSE](LICENSE) contains the unmodified
license text; [NOTICE](NOTICE) applies it to Fraktal and preserves attribution.
This choice is version 3 only, not an automatic grant for future AGPL versions.

The AGPL-3.0-only transition was published on 2026-10-04. Earlier Fraktal
versions were released under MIT. [LICENSES/MIT-legacy.txt](LICENSES/MIT-legacy.txt)
preserves the complete previous copyright, permission and warranty notice.
On 2026-10-05, the public repository was replaced with a fresh repository
containing one initial commit of the validated current AGPL snapshot.
The previous repository is retained privately as a recovery archive; its
commits, branches and tags are not part of the new public Git history.
Historical evidence files remain unchanged. This replacement does not
revoke previously granted MIT permissions or remove copies held elsewhere.

Existing clones should be recreated from the current repository. Preserve
unpublished work separately and reapply it to the new history; do not merge or
push old branches, which would restore the removed MIT-era history. Commit
identifiers in historical evidence continue to identify the original runs.

## Earlier versions and existing permissions

Changing the current license does not cancel MIT permissions already granted.
Recipients can continue using, copying, modifying, distributing and selling
those earlier versions under MIT, provided they meet its notice requirement.
Deleting tags, releases or Git history would not revoke their copies or grants.
Already released MIT material does not become exclusively AGPL merely because
the current distribution is offered under AGPL. Later Fraktal contributions
are not offered under MIT by retaining the historical notice.

Existing MIT material can be included in the current distribution while its
notice is retained. Git author names are not proof of copyright ownership or
assignment. Do not remove another author's notices or assume permission to
relicense separately licensed material. Future contributions follow
[CONTRIBUTING.md](CONTRIBUTING.md); no copyright assignment or commercial
relicensing right is implied.

## What AGPL changes

AGPL permits commercial use, copying, modification and sale. It provides
copyleft and source availability, rather than a ban on competing products.
Redistribution of covered modified works must comply with its licensing and
Corresponding Source requirements. Section 13 also requires a modified program
that supports remote network interaction to prominently offer its Corresponding
Source to those users, at no charge. These duties are not a requirement to
publish every unrelated application on the same computer or network.

For a Fraktal release or a deployed modified HMI/gateway:

- Include LICENSE, NOTICE, the historical MIT notice and applicable dependency
  notices with the distribution. Preserve the original third-party licenses.
- Identify the exact source revision and local modifications. Supply the
  Corresponding Source, including the needed build/install scripts, through a
  method permitted by the license. A link to a moving main branch is not an
  adequate record of a deployed version with unpublished changes.
- For a modified network-facing program, provide the prominent source offer
  required by section 13. Establish that offer for the deployed version before
  representing a package or installation as compliant. This license transition
  alone does not implement a source-offer UI or audit an existing installation.
- Review combined PLC/application distributions and dependencies under the
  actual license definitions. Fraktal does not grant an exception for proprietary
  station code or blanket permission to combine every vendor library. An
  industrial controller deployment can convey covered object code too.

Ordinary parameter-set JSON/data exports are not automatically AGPL because
Fraktal generated them. Generated PLC programs that incorporate Fraktal runtime
code need assessment as covered works; section 2 distinguishes program outputs
by their content. Do not include deployment secrets or credentials in a public
source archive; retain the code and non-secret configuration needed to build it.

## Third-party scope

The project license applies to Fraktal's work and current distribution as a
whole. Separately licensed dependencies and vendor software retain their terms.
Bundled open62541 remains MPL-2.0 at
[its existing license](FraktalCore/HMI/native/opcua/third_party/open62541/LICENSE).
Flutter/Dart dependencies retain their package notices. Historical external
artifacts, quoted license texts and evidence do not acquire new authorship or
lose their original notices through this transition.

The [SPDX AGPL text](https://spdx.org/licenses/AGPL-3.0-only.html) is the reference
for sections 1–6 and 13; the [MIT terms](https://opensource.org/license/mit)
describe the earlier permissions and notice requirement. The full licenses
govern; this document explains the project's intent and release practice.
