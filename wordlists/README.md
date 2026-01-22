# SecLists Integration

Wordlists from [danielmiessler/SecLists](https://github.com/danielmiessler/SecLists) (68K+ stars).

## Installation

\`\`\`bash
cd wordlists
git clone --depth 1 --filter=blob:none --sparse https://github.com/danielmiessler/SecLists.git temp
cd temp
git sparse-checkout set Discovery/Web-Content Fuzzing Payloads Usernames Passwords/Common-Credentials Ai
cp -r Discovery Fuzzing Passwords Usernames Payloads Ai ..
cd .. && rm -rf temp
\`\`\`

## Usage

\`\`\`python
from deadman_scraper.utils import load_wordlist, load_category

# Load specific wordlist
sqli_payloads = load_wordlist("Fuzzing/SQLi/quick-SQLi.txt")

# Load category
discovery = load_category("discovery")
\`\`\`

## Categories

| Category | Files | Use Case |
|----------|-------|----------|
| Discovery | 500+ | Path fuzzing, enumeration |
| Fuzzing | 200+ | SQLi, XSS, LFI payloads |
| Passwords | 50+ | Credential testing |
| Usernames | 30+ | Username enumeration |
| Ai | 10+ | AI-specific lists |
