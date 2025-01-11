import requests
import re
import fanficfare
import subprocess
from bs4 import BeautifulSoup
import time
import os


def extract_https_links_from_file(input_file, output_file):
    try:
        # Read the content of the input file with utf-8 encoding
        with open(input_file, 'r', encoding='utf-8') as file:
            content = file.read()

        # Use regex to find all https:// links
        https_links = re.findall(r'https://[^\s]+', content)

        # Ensure the directory for the output file exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Write the extracted links to the output file without https:// prefix
        with open(output_file, 'w', encoding='utf-8') as file:
            for link in https_links:
                file.write(link.replace('https://', '') + '\n')

        print(f"Extracted {len(https_links)} HTTPS links and saved to {output_file}")

    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


def scrape_ao3_tag(tag, delay=2):
    base_url = "https://archiveofourown.org"
    search_url = f"{base_url}/tags/{tag}/works"
    
    # Ensure the directory for the tag exists
    os.makedirs(tag, exist_ok=True)
    
    with open(os.path.join(tag, "ao3_stories.txt"), "w", encoding="utf-8") as file:
        while search_url:
            print(f"Scraping page: {search_url}")
            
            # Send a GET request to the search URL
            response = requests.get(search_url)
            
            # Check if the request was successful
            if response.status_code != 200:
                print(f"Failed to retrieve the page. Status code: {response.status_code}")
                break
            
            # Parse the HTML content using BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all story blocks
            story_blocks = soup.find_all('li', class_='work')
            
            for block in story_blocks:
                # Extract the word count
                word_count_element = block.find('dd', class_='words')
                if not word_count_element:
                    print("Skipping story: Word count not found")
                    continue  # Skip if word count is not found
                
                try:
                    # Remove commas and convert to integer
                    word_count = int(word_count_element.text.replace(',', ''))
                except ValueError:
                    print(f"Skipping story: Invalid word count '{word_count_element.text}'")
                    continue  # Skip if word count is invalid
                
                # Skip stories with less than 4000 words
                if word_count < 4000:
                    print(f"Skipping story: Word count ({word_count}) is less than 4000")
                    continue
                
                # Extract the story title
                title_element = block.find('h4', class_='heading').find('a')
                if not title_element:
                    print("Skipping story: Title not found")
                    continue  # Skip if title is not found
                
                story_title = title_element.text.strip()
                story_url = base_url + title_element['href']

                # Extract the language
                language_element = block.find('dd', class_='language')
                if not language_element or language_element.text.strip().lower() != 'english':
                     print("Skipping story: Not in English")
                     continue  # Skip if language is not English
                
                # Extract the tags
                tags_element = block.find('ul', class_='tags')
                tags = []
                if tags_element:
                    for tag_element in tags_element.find_all('a', class_='tag'):
                        tags.append(tag_element.text.strip())
                
                # Write the story details to the file
                file.write(f"Story Title: {story_title}\n")
                file.write(f"Story URL: {story_url}\n")
                file.write(f"Word Count: {word_count}\n")
                file.write(f"Tags: {', '.join(tags)}\n")
                file.write("-" * 40 + "\n")
            
            # Find the "Next" button/link for pagination
            next_link = soup.find('a', text='Next →')
            if next_link:
                search_url = base_url + next_link['href']
            else:
                search_url = None  # No more pages, exit the loop
            
            # Rate limiting: Add a delay between requests
            print(f"Waiting {delay} seconds before the next request...")
            time.sleep(delay)
    
    print(f"Results saved to 'ao3_stories.txt'.")

if __name__ == "__main__":
    tag = input("Enter the tag you want to scrape: ")
    delay = int(input("Enter the delay between requests (in seconds, e.g., 2): "))
    scrape_ao3_tag(tag, delay)
    
    try:
        extract_https_links_from_file(os.path.join(tag, "ao3_stories.txt"), os.path.join(tag, "cleaned.txt"))
        print("URLs extracted to 'cleaned.txt'.")
    except Exception as e:
        print(f"An error occurred while extracting URLs: {e}")
    
    try:
        # Run fanficfare with the cleaned.txt file
        subprocess.run([
            "fanficfare",
            "-i", os.path.join(tag, "cleaned.txt"),
            "-p",
            "-o", "output_filename=downloaded/${title}-${siteabbrev}_${authorId}_${storyId}${formatext}"
        ], check=True)
        print("FanFicFare completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"FanFicFare failed with error: {e}")
    except FileNotFoundError:
        print("FanFicFare is not installed or not found in the system PATH.")