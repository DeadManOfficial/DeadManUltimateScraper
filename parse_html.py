from bs4 import BeautifulSoup
import json
import sys
import os

def extract_and_save_html(json_file_path, output_html_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        html_content = data.get('content', '')

    with open(output_html_file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTML content extracted and saved to: {output_html_file_path}")

def explore_html_structure(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    main_content = soup.find('div', {'role': 'article'}) or \
                   soup.find('div', {'role': 'main'}) or \
                   soup.find('div', id='content') or \
                   soup.find('div', id='main') or \
                   soup.find('div', id='post')

    if main_content:
        print("--- Content within a specific container was found ---")
        print("\n--- HEADINGS ---")
        for h_tag in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            print(f"<{h_tag.name}> {h_tag.get_text(strip=True)}")

        print("\n--- PARAGRAPHS ---")
        for p_tag in main_content.find_all('p'):
            print(f"<p> {p_tag.get_text(strip=True)}")
    else:
        print("Could not find a specific content container. It is likely that the content is rendered with JavaScript in a way that is not captured in the static HTML.")
        print("Consider using the --llm flag for extraction with the deadman scrape command.")


def extract_tools_from_html(html_content):
    # This function will be refined later
    soup = BeautifulSoup(html_content, 'html.parser')
    tools = []
    
    # Placeholder for actual extraction logic
    return tools


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "extract-html":
        json_file = sys.argv[2]
        output_html_file = sys.argv[3]
        extract_and_save_html(json_file, output_html_file)
    elif len(sys.argv) > 1 and sys.argv[1] == "explore":
        html_file_path = sys.argv[2]
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content_pure = f.read()
        explore_html_structure(html_content_pure)
    elif len(sys.argv) > 1:
        # This is for final extraction after exploration
        html_file_path = sys.argv[1]
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content_pure = f.read()
        extracted_tools = extract_tools_from_html(html_content_pure)
        print(json.dumps(extracted_tools, indent=2))
    else:
        print("Usage to extract HTML: python parse_html.py extract-html <path_to_json_html_file> <output_html_file_path>")
        print("Usage to explore pure HTML: python parse_html.py explore <path_to_pure_html_file>")
        print("Usage to parse pure HTML: python parse_html.py <path_to_pure_html_file>")
