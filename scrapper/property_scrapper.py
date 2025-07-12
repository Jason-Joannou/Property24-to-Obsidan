import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import os
from scrapper.obsidian_note_generator import PropertyNoteGenerator

class PropertyScrapper:
    def __init__(self) -> None:
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def clean_text(self, text):
        """Clean and normalize text"""
        if not text:
            return ""
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[²\u00b2]', '2', text)
        money_match = re.match(r'^R\s*([\d\s,]+)', text)
        if money_match:
            text = float(money_match.group(1).replace(' ', '').replace(',', ''))
        return text
    
    def to_snake_case(self, text):
        if not text:
            return ""
        # Remove leading/trailing spaces, replace spaces with underscores, and lowercase
        text = text.strip()
        text = re.sub(r'\s+', '_', text)  # Replace spaces (or multiple spaces) with _
        text = re.sub(r'[^\w_]', '', text)  # Remove non-word characters except underscore
        return text.lower()
    
    def extract_number(self, text):
        """Extract numbers from text"""
        if not text:
            return ""
        numbers = re.findall(r'[\\d,]+', str(text))
        return numbers[0].replace(',', '') if numbers else ""
    
    def extract_property_overview(self, listing_number: str, soup: BeautifulSoup):
        """Extract detailed property overview data from the accordion section"""
        overview_data = {}
        poi_url = f"https://www.property24.com/ListingReadOnly/PointsOfInterestForListing?ListingNumber={listing_number}"
        
        # Find the property overview accordion
        overview_section = soup.find('div', class_='p24_listingCard p24_propertyOverview')
        
        if not overview_section:
            return overview_data
        
        # Extract every panel inside the overview - the panels will be our key information and thier rows our values.
        panels = overview_section.find_all('div', class_='panel')
        for panel in panels:
            key_elem = panel.find('div', class_="panel-heading")
            key_text = self.to_snake_case(key_elem.get_text(strip=True))
            if key_text:
                overview_data[key_text] = {}
                panel_rows = panel.find_all('div', class_='p24_propertyOverviewRow')
                if key_text == "points_of_interest":
                    response = requests.get(poi_url, headers=self.headers)
                    if response.status_code == 200:
                        poi_soup = BeautifulSoup(response.content, 'html.parser')
                        poi_categories = poi_soup.find_all('div', class_='js_P24_POICategory')

                        poi_data = {}
                        for category in poi_categories:
                            category_name_elem = category.find('span', class_='p24_semibold')
                            if not category_name_elem:
                                continue
                            category_name = self.to_snake_case(self.clean_text(category_name_elem.get_text(strip=True)))

                            places = []
                            rows = category.find_all('div', class_='row')
                            for row in rows[1:]:  # skip first row (header)
                                cols = row.find_all('div', class_='col-6')
                                if len(cols) >= 2:
                                    place_name = self.clean_text(cols[0].get_text(strip=True))
                                    distance = self.clean_text(cols[1].get_text(strip=True))
                                    places.append({
                                        'name': place_name,
                                        'distance': distance
                                    })

                            poi_data[category_name] = places

                        overview_data[key_text] = poi_data
                else:
                    for row in panel_rows:
                        key_elem = row.find('div', class_='p24_propertyOverviewKey')
                        value_elem = row.find('div', class_='noPadding')
                        if key_text == "rooms":
                            values = []
                            for value in value_elem.find_all('div', class_='p24_info'):
                                value = self.clean_text(value.get_text(strip=True))
                                values.append(value)
                            overview_data[key_text][self.to_snake_case(self.clean_text(key_elem.get_text(strip=True)))] = values[0] if len(values) == 1 else values
                        else:
                            overview_data[key_text][self.to_snake_case(self.clean_text(key_elem.get_text(strip=True)))] = self.clean_text(value_elem.get_text(strip=True))
        
        return overview_data
    
    
    def extract_key_features(self, soup: BeautifulSoup):
        """Extract key features from the p24_keyFeaturesContainer section"""
        key_features = {}
        
        # Find the key features containers
        feature_containers = soup.find_all('div', class_='p24_keyFeaturesContainer')
        
        for container in feature_containers:
            # Find all listing features in this container
            listing_features = container.find_all('div', class_='p24_listingFeatures')
            
            for feature in listing_features:
                # Get the feature name and amount
                feature_name_elem = feature.find('span', class_='p24_feature')
                feature_amount_elem = feature.find('span', class_='p24_featureAmount')
                
                if feature_name_elem:
                    feature_name = self.to_snake_case(self.clean_text(feature_name_elem.get_text()).lower().replace(':', ''))
                    
                    if feature_amount_elem:
                        # Feature with amount (e.g., "Bedrooms: 2")
                        feature_amount = self.clean_text(feature_amount_elem.get_text())
                        key_features[feature_name] = feature_amount
                    else:
                        # Feature without amount (e.g., "Pet Friendly", "Pool")
                        key_features[feature_name] = True
        
        return key_features
    
    def extract_from_json_ld(self, soup: BeautifulSoup):
        """Extract data from JSON-LD structured data"""
        json_scripts = soup.find_all('script', type='application/ld+json')
        
        if not json_scripts:
            return {}
        
        # Extract JSON-LD data
        script = json_scripts[0]
        json_data = json.loads(script.string)
        graph_data = json_data.get('@graph', [])
        
        if not graph_data:
            return {}
        
        property_information = graph_data[0]
        final_info = dict()
        final_info["listing_date"] = property_information.get("datePosted")
        final_info["listing_name"] = property_information.get("name")
        final_info["listing_image"] = property_information.get("image")

        # Extract breadcrumb information to get Province, City, Suburb, ListingID
        # Assuming Property 24 doesnt change its structure positions 2 - 4 are location specific
        breadcrumb_list = property_information.get("breadcrumb", {}).get("itemListElement", [])
        for breadcrumb_item in breadcrumb_list:
            if breadcrumb_item.get("position") == 2:
                final_info["province"] = breadcrumb_item.get("name")
            elif breadcrumb_item.get("position") == 3:
                final_info["city"] = breadcrumb_item.get("name")
            elif breadcrumb_item.get("position") == 4:
                final_info["suburb"] = breadcrumb_item.get("name")
            elif breadcrumb_item.get("position") == 5:
                listing_id = breadcrumb_item.get("name").split(":")[1].strip()
                final_info["listing_id"] = listing_id
        
        # About information
        about_info = property_information.get("about", {})
        final_info["property_type"] = about_info.get("@type")
        final_info["bedrooms"] = about_info.get("numberOfBedrooms")
        final_info["bathrooms"] = about_info.get("numberOfBathroomsTotal")
        final_info["floor_size"] = about_info.get("floorSize", {}).get("value")
        final_info["allowed_pets"] = about_info.get("petsAllowed")
        final_info["address"] = about_info.get("address", {}).get("streetAddress")
        final_info["country"] = about_info.get("address", {}).get("addressCountry")
        final_info["latitude"] = about_info.get("latitude")
        final_info["longitude"] = about_info.get("longitude")

        # Offer Information
        offers_info = property_information.get("offers", {})
        final_info["price"] = offers_info.get("priceSpecification", {}).get("price")
        final_info["price_currency"] = offers_info.get("priceSpecification", {}).get("priceCurrency")
        final_info["listing_organized_by"] = {
            "name": offers_info.get("offeredBy", {}).get("name"),
            "offered_by": offers_info.get("offeredBy", {}).get("@type"),
            "agent_url": offers_info.get("offeredBy", {}).get("url"),
            "works_for": {
                "relation": offers_info.get("offeredBy", {}).get("worksFor", {}).get("@type"),
                "name": offers_info.get("offeredBy", {}).get("worksFor", {}).get("name"),
                "works_for_url": offers_info.get("offeredBy", {}).get("worksFor", {}).get("url")
            }
        }        
        return final_info
    
    
    def scrape_property24(self, url):
        """Enhanced Property24 scraper with all features"""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Start with basic data
            property_data = {
                'url': url,
                'source': 'Property24',
                'scraped_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Extract from JSON-LD first (most reliable)
            json_data = self.extract_from_json_ld(soup)
            if json_data:
                property_data.update(json_data)
            
            # Extract detailed property overview data
            property_data['property_overview'] = self.extract_property_overview(listing_number=property_data['listing_id'], soup=soup)
            
            # Extract key features from the main listing card
            property_data['key_features'] = self.extract_key_features(soup)
            
            return property_data
            
        except Exception as e:
            print(f"Error scraping Property24: {str(e)}")
            return None
    
    def scrape_property(self, url):
        """Main scraping method"""
        if 'property24' in url.lower():
            return self.scrape_property24(url)
        else:
            print("Currently only Property24 URLs are supported")
            return None
    
# Example usage and testing
if __name__ == "__main__":
    # Initialize scraper
    scraper = PropertyScrapper()
    
    # Test URL
    test_url = "https://www.property24.com/for-sale/zonnebloem/cape-town/western-cape/10166/114098915?plId=2083948&plt=3&plsIds=2111336"
    
    print("🚀 Testing Complete Property Scraper")
    print(f"URL: {test_url}")
    print()
    
    # Scrape the property
    result = scraper.scrape_property(test_url)
    note_generator = PropertyNoteGenerator(property_location="Cape Town", note_name="test")
    
    if result:
        # Display results
        # scraper.display_results(result)
        
        # Generate Obsidian note
        result = note_generator.generate_obsidian_note(property_data=result)
        note_generator.save_note_to_obsidian(note_data=result)