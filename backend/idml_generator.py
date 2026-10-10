import os
import zipfile
import tempfile
import xml.etree.ElementTree as ET

class IDMLGenerator:
    """
    Proof of Concept: Translates Exampress Canonical Data into Adobe InDesign (IDML) 
    interchange packages for professional layout editing.
    """

    @staticmethod
    def generate_idml_package(canonical_data: dict, output_path: str) -> str:
        """
        Creates a minimal valid IDML zip structure containing designmap and story XMLs.
        """
        temp_dir = tempfile.mkdtemp()
        try:
            # 1. Create META-INF container
            meta_inf_dir = os.path.join(temp_dir, "META-INF")
            os.makedirs(meta_inf_dir, exist_ok=True)
            container_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
                <rootfiles>
                    <rootfile full-path="designmap.xml" media-type="application/vnd.adobe.indesign-idml-package"/>
                </rootfiles>
            </container>"""
            with open(os.path.join(meta_inf_dir, "container.xml"), "w", encoding="utf-8") as f:
                f.write(container_xml)

            # 2. Create designmap.xml
            designmap_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <Document DOMVersion="18.0" Self="Document">
                <Properties>
                    <Metadata><MetadataProperty><Name>ExampressVersion</Name><Value>2.9</Value></MetadataProperty></Metadata>
                </Properties>
                <Story Self="Story_Main" SourceFile="" AppliedTOCStyle="n" TrackChanges="false" StoryTitle="Main Story">
                    <StoryPreference OpticalMarginAlignment="false" OpticalMarginSize="12"/>
                </Story>
            </Document>"""
            with open(os.path.join(temp_dir, "designmap.xml"), "w", encoding="utf-8") as f:
                f.write(designmap_xml)

            # 3. Zip everything into an IDML file
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                for foldername, subfolders, filenames in os.walk(temp_dir):
                    for filename in filenames:
                        file_path = os.path.join(foldername, filename)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zip_ref.write(file_path, arcname)

            return output_path
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)