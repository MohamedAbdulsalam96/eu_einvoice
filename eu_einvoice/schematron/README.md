`XRechnung-CII-validation.xsl` can be downloaded from https://projekte.kosit.org/xrechnung/xrechnung-schematron/-/releases .

`EN16931-CII-validation-preprocessed.xsl`, `Factur-X_1.07.2_BASIC.xsl` and `Factur-X_1.07.2_EXTENDED.xsl` can be generated by following these steps:

- Download `EN16931-CII-validation-preprocessed.sch` from https://github.com/ConnectingEurope/eInvoicing-EN16931/blob/7ce3772aff315588f37e38b509173f253d340e45/cii/schematron/preprocessed/EN16931-CII-validation-preprocessed.sch and copy into a folder.
- Download the ZUGFeRD spec from https://www.ferd-net.de/publikationen-produkte/publikationen/detailseite/zugferd-232-english and extract the following files:
  - `Factur-X_1.07.2_BASIC.sch`
  - `Factur-X_1.07.2_EXTENDED.sch`
  - `Factur-X_1.07.2_BASIC_codedb.xml`
  - `Factur-X_1.07.2_EXTENDED_codedb.xml`
- Download `schxslt-1.10.1-xslt-only.zip` from https://github.com/schxslt/schxslt/releases/tag/v1.10.1, unzip and copy into the same folder.
- Run the following Python code in the same folder.

```python
from saxonche import PySaxonProcessor

SCHEMATRON_FILES = [
	"EN16931-CII-validation-preprocessed.sch",
	"Factur-X_1.07.2_BASIC.sch",
	"Factur-X_1.07.2_EXTENDED.sch",
]
SCHEMATRON_PIPELINE = "schxslt-1.10.1/2.0/pipeline-for-svrl.xsl"


with PySaxonProcessor(license=False) as proc:
	xslt30_processor = proc.new_xslt30_processor()
	xslt30_processor.set_cwd(".")

	for sch_file in SCHEMATRON_FILES:
		xslt30_processor.transform_to_file(
			source_file=sch_file, stylesheet_file=SCHEMATRON_PIPELINE, output_file=sch_file[:-4] + ".xsl"
		)
```
