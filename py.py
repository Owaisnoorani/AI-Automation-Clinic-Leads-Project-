import json
import csv
import requests
import re
import time
import os
from bs4 import BeautifulSoup
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='website_scraper.log'
)

class WebsiteScraper:
    def __init__(self, competitors):
        """
        Initialize the website scraper with competitors to check for
        
        Args:
            competitors (list): List of competitor names to look for
        """
        self.competitors = [comp.lower() for comp in competitors]
        self.results_directory = "filtered_results"
        
        # Create results directory if it doesn't exist
        if not os.path.exists(self.results_directory):
            os.makedirs(self.results_directory)
    
    def load_urls_from_json(self, json_file_path):
        """
        Load URLs from a JSON file
        
        Args:
            json_file_path (str): Path to the JSON file
            
        Returns:
            list: List of URLs
        """
        urls = []
        try:
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                # Assuming JSON is a list of dictionaries and URLs are in a "url" key
                for item in data:
                    if 'url' in item:
                        urls.append(item['url'])
            
            print(f"Loaded {len(urls)} URLs from {json_file_path}")
            logging.info(f"Loaded {len(urls)} URLs from {json_file_path}")
            return urls
        except Exception as e:
            print(f"Error loading URLs from {json_file_path}: {str(e)}")
            logging.error(f"Error loading URLs from {json_file_path}: {str(e)}")
            return []
    
    def check_competitor_presence(self, url):
        """
        Check if any competitor name is present in the website
        
        Args:
            url (str): URL to check
            
        Returns:
            tuple: (bool, str) - Whether a competitor is found and which one
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get the page text
            page_text = soup.get_text().lower()
            page_html = response.text.lower()
            
            # Check for competitor names in the page text and HTML
            for competitor in self.competitors:
                if competitor in page_text or competitor in page_html:
                    return True, competitor
            
            # Check specifically in the footer
            footer = soup.find('footer')
            if footer:
                footer_text = footer.get_text().lower()
                for competitor in self.competitors:
                    if competitor in footer_text:
                        return True, competitor
            
            return False, None
        except Exception as e:
            logging.error(f"Error checking {url}: {str(e)}")
            return False, None
    
    def extract_clinic_data(self, url, competitor):
        """
        Extract required data from a clinic website
        
        Args:
            url (str): URL of the website
            competitor (str): Competitor name found
            
        Returns:
            dict: Extracted clinic data
        """
        clinic_data = {
            "clinic_name": "",
            "provider_name": "",
            "credentials": "",
            "website_url": url,
            "city_state": "",
            "contact_info": "",
            "website_provider": competitor
        }
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract clinic name
            if soup.title:
                clinic_data["clinic_name"] = soup.title.string.strip()
            else:
                h1_tags = soup.find_all('h1')
                if h1_tags:
                    clinic_data["clinic_name"] = h1_tags[0].get_text().strip()
            
            # Clean up clinic name
            if clinic_data["clinic_name"]:
                # Remove "Home | " or "| Home" patterns
                clinic_data["clinic_name"] = re.sub(r'(Home\s*\|\s*)|(\s*\|\s*Home)', '', clinic_data["clinic_name"])
                # Remove competitor names from title
                for comp in self.competitors:
                    clinic_data["clinic_name"] = re.sub(r'\s*\|\s*' + re.escape(comp), '', clinic_data["clinic_name"], flags=re.IGNORECASE)
            
            # Extract provider name and credentials
            # Try to find sections about doctors or providers
            about_sections = soup.find_all(['div', 'section', 'article'], 
                                          class_=lambda c: c and any(x in c.lower() for x in ['doctor', 'provider', 'team', 'about', 'staff', 'physician']))
            
            # Look for doctor patterns
            doctor_patterns = [
                r'Dr\.\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+),\s+(?:MD|DO|DDS|DMD|DC|DPM|DVM|VMD|PhD)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:MD|DO|DDS|DMD|DC|DPM|DVM|VMD|PhD)'
            ]
            
            credentials_pattern = r'(MD|DO|DDS|DMD|DC|DPM|DVM|VMD|PhD|FACP|FACOG|FACS|FAAP|[A-Z\.]+)'
            
            # Search in about sections first
            for section in about_sections:
                text = section.get_text()
                for pattern in doctor_patterns:
                    match = re.search(pattern, text)
                    if match:
                        clinic_data["provider_name"] = match.group(1)
                        cred_match = re.search(credentials_pattern, text[match.end():match.end()+50])
                        if cred_match:
                            clinic_data["credentials"] = cred_match.group(1)
                        break
                if clinic_data["provider_name"]:
                    break
            
            # If not found, check the full page
            if not clinic_data["provider_name"]:
                full_text = soup.get_text()
                for pattern in doctor_patterns:
                    match = re.search(pattern, full_text)
                    if match:
                        clinic_data["provider_name"] = match.group(1)
                        cred_match = re.search(credentials_pattern, full_text[match.end():match.end()+50])
                        if cred_match:
                            clinic_data["credentials"] = cred_match.group(1)
                        break
            
            # Extract city and state
            address_elements = soup.find_all(['address', 'div', 'p', 'footer', 'span'], 
                                            class_=lambda c: c and any(x in c.lower() for x in ['address', 'location', 'contact', 'footer']))
            
            city_state_patterns = [
                r'([A-Z][a-zA-Z\s\.]+),\s*([A-Z]{2})\s*\d{5}',  # City, State ZIP
                r'([A-Z][a-zA-Z\s\.]+),\s*([A-Z]{2})',          # City, State
            ]
            
            # Search in address elements first
            for element in address_elements:
                text = element.get_text()
                for pattern in city_state_patterns:
                    match = re.search(pattern, text)
                    if match:
                        clinic_data["city_state"] = f"{match.group(1).strip()}, {match.group(2)}"
                        break
                if clinic_data["city_state"]:
                    break
            
            # If not found, check the full page
            if not clinic_data["city_state"]:
                full_text = soup.get_text()
                for pattern in city_state_patterns:
                    match = re.search(pattern, full_text)
                    if match:
                        clinic_data["city_state"] = f"{match.group(1).strip()}, {match.group(2)}"
                        break
            
            # Extract contact information
            # Look for phone numbers and email addresses
            phone_pattern = r'(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            
            phone_numbers = []
            emails = []
            
            # First look in contact-specific elements
            contact_elements = soup.find_all(['div', 'p', 'span', 'a', 'section'], 
                                            class_=lambda c: c and any(x in c.lower() for x in ['contact', 'phone', 'email', 'tel']))
            
            for element in contact_elements:
                text = element.get_text()
                found_phones = re.findall(phone_pattern, text)
                found_emails = re.findall(email_pattern, text)
                phone_numbers.extend(found_phones)
                emails.extend(found_emails)
            
            # Also check for tel: and mailto: links
            tel_links = soup.find_all('a', href=lambda h: h and h.startswith('tel:'))
            for link in tel_links:
                href = link.get('href')
                phone = href.replace('tel:', '').strip()
                if re.match(phone_pattern, phone):
                    phone_numbers.append(phone)
            
            email_links = soup.find_all('a', href=lambda h: h and h.startswith('mailto:'))
            for link in email_links:
                href = link.get('href')
                email = href.replace('mailto:', '').strip()
                if re.match(email_pattern, email):
                    emails.append(email)
            
            # If still not found, check the full page
            if not phone_numbers:
                full_text = soup.get_text()
                phone_numbers = re.findall(phone_pattern, full_text)
            
            if not emails:
                full_text = soup.get_text()
                emails = re.findall(email_pattern, full_text)
            
            # Format contact info
            contact_info = []
            if phone_numbers:
                # Format phone numbers consistently
                phone = phone_numbers[0]
                phone = re.sub(r'[^\d]', '', phone)  # Remove non-digits
                if len(phone) == 10:
                    formatted_phone = f"({phone[0:3]}) {phone[3:6]}-{phone[6:]}"
                    contact_info.append(formatted_phone)
                else:
                    contact_info.append(phone_numbers[0])
            
            if emails:
                contact_info.append(emails[0])
            
            if contact_info:
                clinic_data["contact_info"] = ' | '.join(contact_info)
            
            return clinic_data
        
        except Exception as e:
            logging.error(f"Error extracting data from {url}: {str(e)}")
            return clinic_data
    
    def process_urls(self, urls):
        """
        Process a list of URLs to check for competitors and extract data
        
        Args:
            urls (list): List of URLs to process
            
        Returns:
            list: List of clinic data dictionaries for URLs with competitors
        """
        results = []
        total_urls = len(urls)
        
        for i, url in enumerate(urls):
            try:
                print(f"Processing {i+1}/{total_urls}: {url}")
                logging.info(f"Processing {i+1}/{total_urls}: {url}")
                
                # Fix URL if needed
                if not url.startswith('http'):
                    url = 'http://' + url
                
                # Check if competitor is present
                has_competitor, competitor = self.check_competitor_presence(url)
                
                if has_competitor:
                    print(f"✅ Found competitor {competitor} at {url}")
                    logging.info(f"Found competitor {competitor} at {url}")
                    clinic_data = self.extract_clinic_data(url, competitor)
                    results.append(clinic_data)
                else:
                    print(f"❌ No competitor found at {url}")
                    logging.info(f"No competitor found at {url}")
                
                # Add a delay to avoid overwhelming the server
                if (i + 1) % 5 == 0:
                    time.sleep(1)
            except Exception as e:
                print(f"Error processing {url}: {str(e)}")
                logging.error(f"Error processing {url}: {str(e)}")
        
        return results
    
    def save_results_to_csv(self, results, output_file=None):
        """
        Save the results to a CSV file
        
        Args:
            results (list): List of clinic data dictionaries
            output_file (str, optional): Output file path
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{self.results_directory}/competitor_clinics_{timestamp}.csv"
        
        # Write results to CSV
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    "clinic_name", "provider_name", "credentials", "website_url", 
                    "city_state", "contact_info", "website_provider"
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for result in results:
                    writer.writerow(result)
            print(f"Results saved to {output_file}")
            logging.info(f"Results saved to {output_file}")
        except Exception as e:
            print(f"Error saving results to CSV: {str(e)}")
            logging.error(f"Error saving results to CSV: {str(e)}")


# Main execution
if __name__ == "__main__":
    # Define your competitors here
    competitors = [
        "Dentalqore",
        "Roya.com",
        "ekwa.com",
        "Tebra",
        "iMatrix",
        "GrowthPlug"
    ]  # Add your competitor names here
    
    # Initialize the scraper
    scraper = WebsiteScraper(competitors)
    
    # Load URLs from the JSON file
    urls = scraper.load_urls_from_json(r"C:\ALL Code\Coding leads\clinic_prospecting_results\json\clinic_prospects_20250313_155630.json")
    
    # Process URLs and extract data
    results = scraper.process_urls(urls)
    
    # Save results to CSV
    scraper.save_results_to_csv(results)