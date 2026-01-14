
from deadman_scraper.extract.extractor import Extractor
from deadman_scraper.core.config import ExtractionConfig

config = ExtractionConfig()
extractor = Extractor(config)
print(f"Extractor attributes: {dir(extractor)}")
if hasattr(extractor, 'extract_metadata'):
    print("SUCCESS: extract_metadata found")
else:
    print("FAILURE: extract_metadata NOT found")
