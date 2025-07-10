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
    
    def extract_from_json_ld(self, soup):
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
    
    def extract_amenities(self, soup):
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
        """Improved Property24 scraper"""
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
            
            # Try to extract from JSON-LD first (most reliable)
            json_data = self.extract_from_json_ld(soup)
            if json_data:
                property_data.update(json_data)
            
            # Fallback to HTML parsing for missing data
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
            
            # Extract amenities
            property_data['amenities'] = self.extract_amenities(soup)
            
            # Extract agent details if not in JSON-LD
            if not property_data.get('agent_name'):
                agent_section = soup.find('div', class_='p24_agentDetails')
                if agent_section:
                    agent_text = agent_section.get_text()
                    # Try to find agent name
                    agent_lines = [line.strip() for line in agent_text.split('\\n') if line.strip()]
                    for line in agent_lines:
                        if len(line) > 3 and not line.isdigit() and 'show' not in line.lower():
                            property_data['agent_name'] = line
                            break
            
            # Extract property description from page content
            if not property_data.get('description'):
                # Look for description in various possible containers
                desc_selectors = [
                    'div[class*="description"]',
                    'div[class*="content"]',
                    'div[class*="detail"]'
                ]
                
                for selector in desc_selectors:
                    desc_elem = soup.select_one(selector)
                    if desc_elem:
                        desc_text = desc_elem.get_text().strip()
                        if len(desc_text) > 50:  # Reasonable description length
                            property_data['description'] = desc_text[:500]  # Limit length
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
        """Display scraped results in a nice format"""
        if not data:
            print("❌ No data to display")
            return
        
        print("🏠 PROPERTY SCRAPING RESULTS")
        print("=" * 60)
        
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
        
        # Property Features
        print(f"\\n🏠 PROPERTY FEATURES:")
        print(f"  Bedrooms: {data.get('bedrooms', 'N/A')}")
        print(f"  Bathrooms: {data.get('bathrooms', 'N/A')}")
        print(f"  Size: {data.get('size', 'N/A')} m²")
        print(f"  Pets Allowed: {data.get('pets_allowed', 'N/A')}")
        
        # Agent Information
        print(f"\\n👤 AGENT INFORMATION:")
        print(f"  Agent Name: {data.get('agent_name', 'N/A')}")
        print(f"  Agency: {data.get('agency_name', 'N/A')}")
        
        # Amenities
        amenities = data.get('amenities', {})
        if amenities:
            print(f"\\n🏢 AMENITIES & FEATURES:")
            for amenity, present in amenities.items():
                if present:
                    print(f"  ✓ {amenity.replace('_', ' ').title()}")
        
        # Description
        description = data.get('description', '')
        if description:
            print(f"\\n📝 DESCRIPTION:")
            print(f"  {description[:200]}{'...' if len(description) > 200 else ''}")
        
        print(f"\\n📊 METADATA:")
        print(f"  Source: {data.get('source', 'N/A')}")
        print(f"  Scraped: {data.get('scraped_date', 'N/A')}")
        
        print("\\n" + "="*60)

# Example usage and testing
if __name__ == "__main__":
    # Initialize scraper
    scraper = PropertyScrapper()
    
    # Test URL (replace with your own)
    test_url = "https://www.property24.com/for-sale/zonnebloem/cape-town/western-cape/10166/114098915?plId=2083948&plt=3&plsIds=2111336"
    
    print("🚀 Testing Property Scraper")
    print(f"URL: {test_url}")
    print()
    
    # Scrape the property
    result = scraper.scrape_property(test_url)
    
    if result:
        # Display results
        scraper.display_results(result)
        
        # Save to JSON file
        # filename = f"property_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        # with open(filename, 'w', encoding='utf-8') as f:
        #     json.dump(result, f, indent=2, ensure_ascii=False)
        
        # print(f"\\n📁 Data saved to: {filename}")
        
    else:
        print("❌ Failed to scrape property data")