import os
import json
import csv
import requests
import time
from bs4 import BeautifulSoup
from datetime import datetime

class ClinicProspectingAgent:
    def __init__(self, serp_api_key):
        """
        Initialize the Clinic Prospecting Agent
        
        Args:
            serp_api_key (str): Your SERP API key
        """
        self.serp_api_key = '77d87ec8c1ccce297827cec0853e1ba998ef337624597b7067af4e36916120a2'
        self.base_url = "https://serpapi.com/search"
        self.results_directory = "clinic_prospecting_results"
        
        # Create results directory if it doesn't exist
        if not os.path.exists(self.results_directory):
            os.makedirs(self.results_directory)
    
    def search_clinics(self, vertical, location, website_provider=None, num_results=50):
        """
        Search for clinics based on vertical, location, and optionally website provider
        
        Args:
            vertical (str): Healthcare vertical (e.g., "dentistry", "veterinary")
            location (str): City or region (e.g., "san diego", "tulsa")
            website_provider (str, optional): Website provider (e.g., "dentalqore", "tebra")
            num_results (int): Number of search results to retrieve
            
        Returns:
            list: List of search results
        """
        # Build search query
        if website_provider:
            query = f"{vertical} {location} {website_provider}"
        else:
            query = f"{vertical} {location}"
            
        # Set up parameters for SERP API request
        params = {
            "api_key": self.serp_api_key,
            "engine": "google",
            "q": query,
            "num": num_results,
            "gl": "us",  # Search in United States
            "hl": "en"   # English language results
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            if "error" in data:
                print(f"Error: {data['error']}")
                return []
                
            # Extract organic search results
            organic_results = data.get("organic_results", [])
            return organic_results
            
        except Exception as e:
            print(f"Search failed: {str(e)}")
            return []
    
    def search_by_copyright(self, website_provider):
        """
        Search for clinics by copyright footer text
        
        Args:
            website_provider (str): Website provider to search for
            
        Returns:
            list: List of search results
        """
        query = f"Medical website powered by {website_provider}"
        
        params = {
            "api_key": self.serp_api_key,
            "engine": "google",
            "q": query,
            "num": 100,
            "gl": "us",
            "hl": "en"
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            if "error" in data:
                print(f"Error: {data['error']}")
                return []
                
            organic_results = data.get("organic_results", [])
            return organic_results
            
        except Exception as e:
            print(f"Copyright search failed: {str(e)}")
            return []
    
    def extract_clinic_data(self, url):
        """
        Extract clinic information from their website
        
        Args:
            url (str): URL of the clinic website
            
        Returns:
            dict: Extracted clinic data
        """
        clinic_data = {
            "name": None,
            "url": url,
            "provider_name": None,
            "credentials": None,
            "city_state": None,
            "contact_info": None,
            "website_provider": None
        }
        
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract clinic name (usually in title or h1)
            title = soup.title.string if soup.title else None
            clinic_data["name"] = title.split("|")[0].strip() if title else None
            
            # Look for provider name and credentials in the page
            # This requires some heuristics as websites vary
            about_page_links = soup.find_all("a", text=lambda t: t and "about" in t.lower())
            if about_page_links:
                # Could follow this link to extract provider details
                pass
            
            # Extract contact information
            contact_elements = soup.find_all(text=lambda t: t and ("@" in t or "phone" in t.lower() or "tel:" in t.lower()))
            if contact_elements:
                clinic_data["contact_info"] = contact_elements[0].strip()
            
            # Extract city/state from address elements
            address_elements = soup.find_all(["address", "div"], class_=lambda c: c and "address" in c.lower())
            if address_elements:
                address_text = address_elements[0].get_text()
                # Use regex or other methods to extract city/state
                clinic_data["city_state"] = address_text.strip()
            
            # Check footer for website provider
            footer = soup.find("footer")
            if footer:
                footer_text = footer.get_text().lower()
                website_providers = ["dentalqore", "roya", "ekwa", "tebra", "imatrix", "growthplug"]
                for provider in website_providers:
                    if provider in footer_text:
                        clinic_data["website_provider"] = provider
                        break
            
            return clinic_data
            
        except Exception as e:
            print(f"Data extraction failed for {url}: {str(e)}")
            return clinic_data
    
    def is_corporate_clinic(self, data):
        """
        Check if the clinic is corporate based on various signals
        
        Args:
            data (dict): Clinic data
            
        Returns:
            bool: True if corporate, False if likely private
        """
        corporate_signals = [
            "health system", "medical group", "hospital", "ascension", 
            "providence", "kaiser", "dignity", "community health", 
            "medical center", "health partners"
        ]
        
        if data["name"]:
            for signal in corporate_signals:
                if signal.lower() in data["name"].lower():
                    return True
        
        return False
    
    def categorize_by_vertical(self, data):
        """
        Categorize clinic by healthcare vertical based on its data
        
        Args:
            data (dict): Clinic data
            
        Returns:
            str: Healthcare vertical
        """
        verticals = {
            "veterinary": ["vet", "animal", "pet", "dvm", "vmd"],
            "dentistry": ["dent", "oral", "dds", "dmd"],
            "cardiology": ["cardio", "heart"],
            "chiropractic": ["chiro", "spine", "dc"],
            "podiatry": ["foot", "ankle", "dpm"],
            "internal medicine": ["internal medicine"],
            "family medicine": ["family"]
        }
        
        if data["name"]:
            name_lower = data["name"].lower()
            for vertical, keywords in verticals.items():
                for keyword in keywords:
                    if keyword in name_lower:
                        return vertical
        
        return "other specialty"
    
    def process_search_results(self, results):
        """
        Process search results to extract clinic data
        
        Args:
            results (list): List of search results
            
        Returns:
            list: Processed clinic data
        """
        processed_data = []
        
        for result in results:
            url = result.get("link")
            if url:
                print(f"Processing: {url}")
                clinic_data = self.extract_clinic_data(url)
                
                # Check if it's a corporate clinic
                if not self.is_corporate_clinic(clinic_data):
                    # Categorize by vertical
                    vertical = self.categorize_by_vertical(clinic_data)
                    clinic_data["vertical"] = vertical
                    processed_data.append(clinic_data)
                
                # Add a small delay to avoid being blocked
                time.sleep(1)
        
        return processed_data
    
    def save_to_csv(self, data, filename=None):
        """
        Save processed clinic data to CSV
        
        Args:
            data (list): List of clinic data dictionaries
            filename (str, optional): Output filename
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.results_directory}/clinic_prospects_{timestamp}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                "name", "vertical", "provider_name", "credentials", 
                "city_state", "contact_info", "website_provider", "url"
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for clinic in data:
                writer.writerow(clinic)
        
        print(f"Results saved to {filename}")
    
    def save_to_json(self, data, filename=None):
        """
        Save processed clinic data to JSON
        
        Args:
            data (list): List of clinic data dictionaries
            filename (str, optional): Output filename
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.results_directory}/clinic_prospects_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=4)
        
        print(f"Results saved to {filename}")
    
    def run_prospecting_campaign(self, verticals, locations, website_providers=None):
        """
        Run a complete prospecting campaign
        
        Args:
            verticals (list): List of healthcare verticals to search
            locations (list): List of locations to search
            website_providers (list, optional): List of website providers to search
            
        Returns:
            list: Complete list of prospects found
        """
        all_prospects = []
        
        # Method 1: Vertical-based search
        for vertical in verticals:
            for location in locations:
                if website_providers:
                    for provider in website_providers:
                        print(f"Searching for {vertical} in {location} using {provider}...")
                        results = self.search_clinics(vertical, location, provider)
                        prospects = self.process_search_results(results)
                        all_prospects.extend(prospects)
                else:
                    print(f"Searching for {vertical} in {location}...")
                    results = self.search_clinics(vertical, location)
                    prospects = self.process_search_results(results)
                    all_prospects.extend(prospects)
                
                # Avoid API rate limits
                time.sleep(2)
        
        # Method 2: Copyright identification method
        if website_providers:
            for provider in website_providers:
                print(f"Searching for websites powered by {provider}...")
                results = self.search_by_copyright(provider)
                prospects = self.process_search_results(results)
                all_prospects.extend(prospects)
                
                # Avoid API rate limits
                time.sleep(2)
        
        # Remove duplicates based on URL
        unique_prospects = []
        unique_urls = set()
        
        for prospect in all_prospects:
            if prospect["url"] not in unique_urls:
                unique_urls.add(prospect["url"])
                unique_prospects.append(prospect)
        
        # Save results
        self.save_to_csv(unique_prospects)
        self.save_to_json(unique_prospects)
        
        return unique_prospects


# Example Usage
def main():
    # Replace with your SERP API key
    SERP_API_KEY = "your_serp_api_key_here"
    
    # Initialize the agent
    agent = ClinicProspectingAgent(SERP_API_KEY)
    
    # Define search parameters
    verticals = [
        "dentistry", 
        "veterinary", 
        "cardiology", 
        "chiropractic",
        "podiatry", 
        "internal medicine", 
        "family medicine"
    ]
    
    locations = [
        "san diego", 
        "los angeles", 
        "new york", 
        "chicago", 
        "houston",
        "phoenix"
    ]
    
    website_providers = [
        "dentalqore", 
        "roya.com", 
        "ekwa.com", 
        "tebra", 
        "imatrix", 
        "growthplug"
    ]
    
    # Run the campaign
    prospects = agent.run_prospecting_campaign(verticals, locations, website_providers)
    print(f"Found {len(prospects)} unique private clinic prospects")


if __name__ == "__main__":
    main()