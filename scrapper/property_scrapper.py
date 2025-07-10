import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import os

class PropertyScrapper:
    def __init__(self) -> None:
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def clean_text(self, text):
        """Clean and normalize text"""
        if not text:
            return ""
        return re.sub(r'\\s+', ' ', text.strip())
    
    def extract_number(self, text):
        """Extract numbers from text"""
        if not text:
            return ""
        numbers = re.findall(r'[\\d,]+', str(text))
        return numbers[0].replace(',', '') if numbers else ""
    
    def extract_property_overview(self, soup: BeautifulSoup):
        """Extract detailed property overview data from the accordion section"""
        overview_data = {}
        
        # Find the property overview accordion
        overview_section = soup.find('div', class_='p24_listingCard p24_propertyOverview')
        if not overview_section:
            return overview_data
        
        # Extract all key-value pairs from the overview rows
        overview_rows = overview_section.find_all('div', class_='p24_propertyOverviewRow')
        
        for row in overview_rows:
            key_elem = row.find('div', class_='p24_propertyOverviewKey')
            value_elem = row.find('div', class_='p24_info')
            
            if key_elem and value_elem:
                key = self.clean_text(key_elem.get_text()).lower().replace(' ', '_')
                value = self.clean_text(value_elem.get_text())
                
                if key and value:
                    overview_data[key] = value
        
        return overview_data
    
    def extract_rooms_details(self, soup: BeautifulSoup):
        """Extract detailed room information"""
        rooms_data = {}
        
        # Find the rooms accordion section
        rooms_section = soup.find('div', id='js_accordion_rooms')
        if not rooms_section:
            return rooms_data
        
        # Extract room details
        room_rows = rooms_section.find_all('div', class_='p24_propertyOverviewRow')
        
        for row in room_rows:
            key_elem = row.find('div', class_='p24_propertyOverviewKey')
            value_elems = row.find_all('div', class_='p24_info')
            
            if key_elem and value_elems:
                key = self.clean_text(key_elem.get_text()).lower().replace(' ', '_')
                values = [self.clean_text(elem.get_text()) for elem in value_elems if elem.get_text().strip()]
                
                if key and values:
                    if len(values) == 1:
                        rooms_data[key] = values[0]
                    else:
                        rooms_data[key] = values
        
        return rooms_data
    
    def extract_external_features(self, soup: BeautifulSoup):
        """Extract external features like parking, pool, etc."""
        external_data = {}
        
        # Find the external features accordion section
        external_section = soup.find('div', id='js_accordion_externalfeatures')
        if not external_section:
            return external_data
        
        # Extract external features
        feature_rows = external_section.find_all('div', class_='p24_propertyOverviewRow')
        
        for row in feature_rows:
            key_elem = row.find('div', class_='p24_propertyOverviewKey')
            value_elem = row.find('div', class_='p24_info')
            
            if key_elem and value_elem:
                key = self.clean_text(key_elem.get_text()).lower().replace(' ', '_')
                value = self.clean_text(value_elem.get_text())
                
                if key and value:
                    external_data[key] = value
        
        return external_data
    
    def extract_points_of_interest(self, soup: BeautifulSoup):
        """Extract points of interest (schools, restaurants, etc.)"""
        poi_data = {}
        
        # Find the points of interest section
        poi_section = soup.find('div', id='P24_pointsOfInterest')
        if not poi_section:
            return poi_data
        
        # Extract POI categories
        poi_categories = poi_section.find_all('div', class_='js_P24_POICategory')
        
        for category in poi_categories:
            # Get category name
            category_name_elem = category.find('span', class_='p24_semibold')
            if not category_name_elem:
                continue
                
            category_name = self.clean_text(category_name_elem.get_text()).lower().replace(' ', '_').replace('_and_', '_')
            
            # Get all POI items in this category
            poi_items = []
            poi_rows = category.find_all('div', class_='row')[1:]  # Skip the header row
            
            for row in poi_rows:
                cols = row.find_all('div', class_='col-6')
                if len(cols) >= 2:
                    name = self.clean_text(cols[0].get_text())
                    distance = self.clean_text(cols[1].get_text())
                    
                    if name and distance and 'view more' not in name.lower():
                        poi_items.append({
                            'name': name,
                            'distance': distance
                        })
            
            if poi_items:
                poi_data[category_name] = poi_items
        
        return poi_data
    
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
                    feature_name = self.clean_text(feature_name_elem.get_text()).lower().replace(':', '').replace(' ', '_')
                    
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
        
        for script in json_scripts:
            try:
                json_data = json.loads(script.string)
                
                if isinstance(json_data, dict) and '@graph' in json_data:
                    for item in json_data['@graph']:
                        if item.get('@type') == 'RealEstateListing':
                            property_info = item.get('about', {})
                            offers_info = item.get('offers', {})
                            
                            return {
                                'title': item.get('name', ''),
                                'description': item.get('description', ''),
                                'price': offers_info.get('priceSpecification', {}).get('price', ''),
                                'currency': offers_info.get('priceSpecification', {}).get('priceCurrency', ''),
                                'bedrooms': property_info.get('numberOfBedrooms', ''),
                                'bathrooms': property_info.get('numberOfBathroomsTotal', ''),
                                'size': property_info.get('floorSize', {}).get('value', ''),
                                'property_type': property_info.get('@type', ''),
                                'address': property_info.get('address', {}).get('streetAddress', ''),
                                'area': property_info.get('address', {}).get('addressLocality', ''),
                                'province': property_info.get('address', {}).get('addressRegion', ''),
                                'latitude': property_info.get('latitude', ''),
                                'longitude': property_info.get('longitude', ''),
                                'pets_allowed': property_info.get('petsAllowed', ''),
                                'agent_name': offers_info.get('offeredBy', {}).get('name', ''),
                                'agency_name': offers_info.get('offeredBy', {}).get('worksFor', {}).get('name', ''),
                                'listing_url': offers_info.get('url', ''),
                                'image_url': item.get('image', ''),
                                'date_posted': item.get('datePosted', '')
                            }
            except Exception as e:
                print(f"Error parsing JSON-LD: {e}")
                continue
        
        return None
    
    def extract_amenities(self, soup: BeautifulSoup):
        """Extract amenities and features from the page"""
        all_text = soup.get_text().lower()
        
        amenity_keywords = {
            'pool': ['pool', 'swimming'],
            'security': ['security', '24-hour', 'access control', 'secure'],
            'gym': ['gym', 'fitness', 'exercise'],
            'parking': ['parking', 'garage', 'carport'],
            'garden': ['garden', 'landscaped', 'outdoor space'],
            'balcony': ['balcony', 'terrace', 'patio'],
            'view': ['view', 'mountain view', 'sea view', 'city view'],
            'kitchen': ['kitchen', 'modern kitchen', 'fitted kitchen'],
            'laundry': ['laundry', 'washing'],
            'elevator': ['elevator', 'lift'],
            'air_conditioning': ['air conditioning', 'aircon', 'climate control'],
            'fireplace': ['fireplace', 'braai']
        }
        
        found_amenities = {}
        for amenity, keywords in amenity_keywords.items():
            for keyword in keywords:
                if keyword in all_text:
                    found_amenities[amenity] = True
                    break
        
        return found_amenities
    
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
            property_data['property_overview'] = self.extract_property_overview(soup)
            
            # Extract room details
            property_data['rooms_details'] = self.extract_rooms_details(soup)
            
            # Extract external features
            property_data['external_features'] = self.extract_external_features(soup)
            
            # Extract points of interest
            property_data['points_of_interest'] = self.extract_points_of_interest(soup)
            
            # Extract key features from the main listing card
            property_data['key_features'] = self.extract_key_features(soup)
            
            # Extract amenities (your original method)
            property_data['amenities'] = self.extract_amenities(soup)
            
            # Fallback to HTML parsing for missing basic data
            all_text = soup.get_text()
            
            # Extract price if not found in JSON-LD
            if not property_data.get('price'):
                price_matches = re.findall(r'R\\s*([\\d\\s,]+)', all_text)
                for price in price_matches:
                    clean_price = re.sub(r'\\s+', '', price).replace(',', '')
                    if clean_price.isdigit() and len(clean_price) >= 6:
                        property_data['price'] = clean_price
                        break
            
            # Extract features if not found in JSON-LD
            feature_patterns = {
                'bedrooms': r'(\\d+)\\s*(?:bed|bedroom)',
                'bathrooms': r'(\\d+)\\s*(?:bath|bathroom)', 
                'parking': r'(\\d+)\\s*(?:parking|garage)',
                'size': r'(\\d+)\\s*m²',
            }
            
            for feature, pattern in feature_patterns.items():
                if not property_data.get(feature):
                    matches = re.findall(pattern, all_text, re.I)
                    if matches:
                        property_data[feature] = matches[0]
            
            # Extract agent details if not in JSON-LD
            if not property_data.get('agent_name'):
                agent_section = soup.find('div', class_='p24_agentDetails')
                if agent_section:
                    agent_text = agent_section.get_text()
                    agent_lines = [line.strip() for line in agent_text.split('\\n') if line.strip()]
                    for line in agent_lines:
                        if len(line) > 3 and not line.isdigit() and 'show' not in line.lower():
                            property_data['agent_name'] = line
                            break
            
            # Extract property description from page content
            if not property_data.get('description'):
                desc_selectors = [
                    'div[class*="description"]',
                    'div[class*="content"]',
                    'div[class*="detail"]'
                ]
                
                for selector in desc_selectors:
                    desc_elem = soup.select_one(selector)
                    if desc_elem:
                        desc_text = desc_elem.get_text().strip()
                        if len(desc_text) > 50:
                            property_data['description'] = desc_text[:500]
                            break
            
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
    
    def display_results(self, data):
        """Display scraped results in a comprehensive format"""
        if not data:
            print("❌ No data to display")
            return
        
        print("🏠 COMPLETE PROPERTY SCRAPING RESULTS")
        print("=" * 70)
        
        # Basic Information
        print("📋 BASIC INFORMATION:")
        print(f"  Title: {data.get('title', 'N/A')}")
        print(f"  Property Type: {data.get('property_type', 'N/A')}")
        print(f"  Address: {data.get('address', 'N/A')}")
        print(f"  Area: {data.get('area', 'N/A')}")
        print(f"  Province: {data.get('province', 'N/A')}")
        
        # Financial Information
        print(f"\\n💰 FINANCIAL INFORMATION:")
        price = data.get('price', '0')
        if price and price.isdigit():
            print(f"  Price: R{int(price):,} {data.get('currency', '')}")
        else:
            print(f"  Price: {price}")
        print(f"  Date Posted: {data.get('date_posted', 'N/A')}")
        
        # Property Overview Details
        overview = data.get('property_overview', {})
        if overview:
            print(f"\\n📊 PROPERTY OVERVIEW:")
            for key, value in overview.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Key Features (from the main card)
        key_features = data.get('key_features', {})
        if key_features:
            print(f"\\n🔑 KEY FEATURES:")
            for feature, value in key_features.items():
                if isinstance(value, bool):
                    print(f"  ✓ {feature.replace('_', ' ').title()}")
                else:
                    print(f"  {feature.replace('_', ' ').title()}: {value}")
        
        # Amenities (from text analysis)
        amenities = data.get('amenities', {})
        if amenities:
            print(f"\\n🏢 AMENITIES (detected from text):")
            for amenity, present in amenities.items():
                if present:
                    print(f"  ✓ {amenity.replace('_', ' ').title()}")
        
        # Room Details
        rooms = data.get('rooms_details', {})
        if rooms:
            print(f"\\n🏠 ROOM DETAILS:")
            for key, value in rooms.items():
                if isinstance(value, list):
                    print(f"  {key.replace('_', ' ').title()}: {', '.join(value)}")
                else:
                    print(f"  {key.replace('_', ' ').title()}: {value}")
        
        # External Features
        external = data.get('external_features', {})
        if external:
            print(f"\\n🌳 EXTERNAL FEATURES:")
            for key, value in external.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Points of Interest (show summary)
        poi = data.get('points_of_interest', {})
        if poi:
            print(f"\\n📍 POINTS OF INTEREST:")
            for category, items in poi.items():
                print(f"  {category.replace('_', ' ').title()}: {len(items)} items")
                for item in items[:2]:  # Show first 2 items
                    print(f"    • {item['name']} ({item['distance']})")
                if len(items) > 2:
                    print(f"    ... and {len(items) - 2} more")
        
        # Agent Information
        print(f"\\n👤 AGENT INFORMATION:")
        print(f"  Agent Name: {data.get('agent_name', 'N/A')}")
        print(f"  Agency: {data.get('agency_name', 'N/A')}")
        
        # Description
        description = data.get('description', '')
        if description:
            print(f"\\n📝 DESCRIPTION:")
            print(f"  {description[:200]}{'...' if len(description) > 200 else ''}")
        
        print(f"\\n📊 METADATA:")
        print(f"  Source: {data.get('source', 'N/A')}")
        print(f"  Scraped: {data.get('scraped_date', 'N/A')}")
        
        print("\\n" + "="*70)

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
    
    if result:
        # Display results
        scraper.display_results(result)
        
    else:
        print("❌ Failed to scrape property data")