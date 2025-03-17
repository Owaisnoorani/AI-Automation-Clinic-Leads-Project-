import csv
import requests
import re
import time
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime

class WebsiteScraper:
    def __init__(self, competitors):
        """
        Initialize the website scraper with competitors to check for
        
        Args:
            competitors (list): List of competitor names to look for
        """
        self.competitors = [comp.lower() for comp in competitors]
        self.results_directory = "scraping_results"
        
        # Create results directory if it doesn't exist
        if not os.path.exists(self.results_directory):
            os.makedirs(self.results_directory)
    
    def load_urls_from_csv(self, csv_file):
        """
        Load URLs from a CSV file
        
        Args:
            csv_file (str): Path to the CSV file containing URLs
            
        Returns:
            list: List of URLs
        """
        urls = []
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                for row in reader:
                    if row and row[0].startswith('http'):
                        urls.append(row[0].strip())
                    elif row and not row[0].startswith('http'):
                        # Add http:// if missing
                        urls.append(f"http://{row[0].strip()}")
            
            print(f"Loaded {len(urls)} URLs from {csv_file}")
            return urls
        except Exception as e:
            print(f"Error loading URLs from CSV: {str(e)}")
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
            response = requests.get(url, headers=headers, timeout=10)
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
            print(f"Error checking {url}: {str(e)}")
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
            "clinic_name": None,
            "provider_name": None,
            "credentials": None,
            "website_url": url,
            "city_state": None,
            "contact_info": None,
            "website_provider": competitor
        }
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract clinic name (usually in title or h1)
            title = soup.title.string if soup.title else None
            if title:
                clinic_data["clinic_name"] = title.split("|")[0].strip()
            else:
                h1 = soup.find('h1')
                if h1:
                    clinic_data["clinic_name"] = h1.get_text().strip()
            
            # Extract provider name and credentials
            # Look for about pages, team pages, or sections with provider info
            about_sections = soup.find_all(['div', 'section'], class_=lambda c: c and ('about' in c.lower() or 'doctor' in c.lower() or 'team' in c.lower()))
            
            credentials_pattern = r'(?:Dr\.|MD|DO|DDS|DMD|DPM|DC|DVM|VMD|PhD|NP|PA)(?:\s*,\s*[A-Z]+)*'
            
            for section in about_sections:
                text = section.get_text()
                credentials_match = re.search(credentials_pattern, text)
                if credentials_match:
                    # Try to extract the full name before the credentials
                    name_match = re.search(r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+' + credentials_pattern, text)
                    if name_match:
                        clinic_data["provider_name"] = name_match.group(1)
                        clinic_data["credentials"] = credentials_match.group(0)
                    break
            
            # Extract city and state
            # Look for address information
            address_elements = soup.find_all(['address', 'div', 'p'], class_=lambda c: c and ('address' in c.lower() or 'location' in c.lower()))
            
            state_pattern = r'[A-Z]{2}'  # Two capital letters for state abbreviation
            zipcode_pattern = r'\d{5}(?:-\d{4})?'  # US ZIP code pattern
            city_state_pattern = r'([A-Z][a-zA-Z\s]+),\s*([A-Z]{2})'  # City, State pattern
            
            for element in address_elements:
                text = element.get_text()
                city_state_match = re.search(city_state_pattern, text)
                if city_state_match:
                    clinic_data["city_state"] = f"{city_state_match.group(1)}, {city_state_match.group(2)}"
                    break
            
            # Extract contact information
            # Look for phone numbers and email addresses
            phone_pattern = r'(?:\+1|1)?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            
            phone_match = re.search(phone_pattern, response.text)
            email_match = re.search(email_pattern, response.text)
            
            contact_info = []
            if phone_match:
                contact_info.append(phone_match.group(0))
            if email_match:
                contact_info.append(email_match.group(0))
            
            if contact_info:
                clinic_data["contact_info"] = ', '.join(contact_info)
            
            return clinic_data
        
        except Exception as e:
            print(f"Error extracting data from {url}: {str(e)}")
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
            print(f"Processing {i+1}/{total_urls}: {url}")
            has_competitor, competitor = self.check_competitor_presence(url)
            
            if has_competitor:
                print(f"Found competitor {competitor} at {url}")
                clinic_data = self.extract_clinic_data(url, competitor)
                results.append(clinic_data)
            
            # Add a delay to avoid overwhelming the server
            if i % 10 == 0 and i > 0:
                time.sleep(2)
        
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
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                "clinic_name", "provider_name", "credentials", 
                "website_url", "city_state", "contact_info", "website_provider"
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in results:
                writer.writerow(result)
        
        print(f"Results saved to {output_file}")
        return output_file
    
    def save_results_to_json(self, results, output_file=None):
        """
        Save the results to a JSON file
        
        Args:
            results (list): List of clinic data dictionaries
            output_file (str, optional): Output file path
        """
        import json
        
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{self.results_directory}/competitor_clinics_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as jsonfile:
            json.dump(results, jsonfile, indent=4)
        
        print(f"Results saved to {output_file}")
        return output_file
    
    def run(self, csv_file):
        """
        Run the complete scraping process
        
        Args:
            csv_file (str): Path to the CSV file containing URLs
            
        Returns:
            tuple: (list of results, output CSV file path)
        """
        # Load URLs from CSV
        urls = self.load_urls_from_csv(csv_file)
        
        if not urls:
            print("No URLs found in the CSV file.")
            return [], None
        
        # Process URLs
        results = self.process_urls(urls)
        
        print(f"Found {len(results)} websites with competitors out of {len(urls)} total URLs.")
        
        # Save results
        output_csv = self.save_results_to_csv(results)
        self.save_results_to_json(results)
        
        return results, output_csv


# Example usage
def main():
    # Define competitors
    competitors = ["Dentalqore", "Roya.com", "ekwa.com", "Tebra", "iMatrix", "GrowthPlug"]
    
    # Create scraper instance
    scraper = WebsiteScraper(competitors)
    
    # Run the scraper
    csv_file = "websites.csv"  # Replace with your actual CSV file path
    results, output_file = scraper.run(csv_file)
    
    # Print summary
    print("\nScraping Summary:")
    print(f"Total websites checked: {len(scraper.load_urls_from_csv(csv_file))}")
    print(f"Websites with competitors found: {len(results)}")
    print(f"Results saved to: {output_file}")


if __name__ == "__main__":
    main()