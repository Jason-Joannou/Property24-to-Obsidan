import re
import json
from datetime import datetime

class PropertyNoteGenerator:

    def __init__(self, property_location: str, note_name: str) -> None:
        self.vault_directory = ""
        self.property_directory = ""
        self.property_location = property_location
        self.note_name = note_name

    def format_currency(self, amount):
        """Format number as currency"""
        if not amount:
            return "R0"
        
        # Handle string amounts like "R 27 000"
        if isinstance(amount, str):
            # Extract numbers from string
            numbers = re.findall(r'[\\d,]+', amount.replace(' ', ''))
            if numbers:
                clean_amount = numbers[0].replace(',', '')
                if clean_amount.isdigit():
                    return f"R{int(clean_amount):,}"
            return amount
        
        # Handle numeric amounts
        if isinstance(amount, (int, float)):
            return f"R{int(amount):,}"
        
        return str(amount)
    
    def safe_string(self, value):
        """Make string safe for YAML frontmatter"""
        if not value:
            return ""
        return str(value).replace('"', "'").replace('\\n', ' ').strip()
    
    def calculate_transfer_duty(self, price):
        """Calculate South African transfer duty"""
        if not price or not str(price).replace(',', '').isdigit():
            return 0
        
        price_num = int(str(price).replace(',', ''))
        
        if price_num <= 1000000:
            return 0
        elif price_num <= 1375000:
            return (price_num - 1000000) * 0.03
        elif price_num <= 1925000:
            return 11250 + (price_num - 1375000) * 0.06
        elif price_num <= 2475000:
            return 44250 + (price_num - 1925000) * 0.08
        else:
            return 88250 + (price_num - 2475000) * 0.11
        
    def generate_dynamic_amenities_frontmatter(self, amenities, key_features):
        """Generate dynamic amenities section for frontmatter as a YAML list"""
        amenities_yaml = ""
        
        # Combine amenities from both sources
        all_amenities = set()  # Use set to avoid duplicates
        
        # Add amenities from text analysis
        if amenities:
            for amenity, present in amenities.items():
                if present:
                    all_amenities.add(amenity)
        
        # Add key features that are boolean (amenities)
        if key_features:
            for feature, value in key_features.items():
                if isinstance(value, bool) and value:
                    all_amenities.add(feature)
        
        # Generate YAML list for amenities
        if all_amenities:
            amenities_yaml = "amenities:\n"
            for amenity in sorted(all_amenities):
                amenities_yaml += f"  - {amenity}\n"
        
        return amenities_yaml.strip()
            
    def calculate_bond_payment(self, principal, rate=0.1175, years=20):
        """Calculate monthly bond payment"""
        if not principal or principal <= 0:
            return 0
        
        monthly_rate = rate / 12
        num_payments = years * 12
        
        if monthly_rate == 0:
            return principal / num_payments
        
        return principal * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
    
    def extract_location_from_title(self, title, area):
        """Extract location for folder organization"""
        if area:
            return area
        
        # Common SA areas
        common_areas = [
            'Sandton', 'Rosebank', 'Claremont', 'Green Point', 'Sea Point', 
            'Camps Bay', 'Constantia', 'Newlands', 'Observatory', 'Woodstock',
            'Cape Town', 'Johannesburg', 'Pretoria', 'Durban', 'Stellenbosch',
            'Bellville', 'Parow', 'Goodwood', 'Milnerton', 'Table View',
            'Zonnebloem', 'Gardens', 'Tamboerskloof', 'De Waterkant'
        ]
        
        title_upper = title.upper()
        for area in common_areas:
            if area.upper() in title_upper:
                return area
        
        return "Unknown Location"
    
    def generate_filename(self, property_data):
        """Generate a clean filename for the property"""
        title = property_data.get('title', 'Property')
        address = property_data.get('address', '')
        area = property_data.get('area', '')
        
        # Use address if available, otherwise title
        base_name = address if address and address != '.' else title
        
        # Clean the filename
        filename = re.sub(r'[^a-zA-Z0-9\\s]', '', base_name)
        filename = re.sub(r'\\s+', '_', filename.strip())
        filename = filename[:50]  # Limit length
        
        # Add area if not in filename
        if area and area.lower() not in filename.lower():
            filename = f"{filename}_{area}"
        
        return f"{filename}.md"
    
    def generate_obsidian_note(self, property_data):
        """Generate comprehensive Obsidian note from scraped property data"""
        if not property_data:
            return None
        
        # Extract basic information
        title = property_data.get('title', 'Unknown Property')
        price_str = property_data.get('price', '0')
        price = int(price_str.replace(',', '')) if str(price_str).replace(',', '').isdigit() else 0
        area = property_data.get('area', '')
        location = self.extract_location_from_title(title, area)
        
        # Get property overview data
        overview = property_data.get('property_overview', {})
        key_features = property_data.get('key_features', {})
        amenities = property_data.get('amenities', {})
        rooms = property_data.get('rooms_details', {})
        external = property_data.get('external_features', {})
        poi = property_data.get('points_of_interest', {})
        
        # Calculate financials
        transfer_duty = self.calculate_transfer_duty(price)
        deposit = price * 0.1
        bond_amount = price - deposit
        monthly_payment = self.calculate_bond_payment(bond_amount)
        
        # Get monthly costs from overview
        levies = overview.get('levies', 'R 0')
        rates_taxes = overview.get('rates_and_taxes', 'R 0')
        
        # Extract numeric values for calculations
        levies_num = int(re.findall(r'[\\d,]+', levies.replace(' ', ''))[0].replace(',', '')) if re.findall(r'[\\d,]+', levies.replace(' ', '')) else 0
        rates_num = int(re.findall(r'[\\d,]+', rates_taxes.replace(' ', ''))[0].replace(',', '')) if re.findall(r'[\\d,]+', rates_taxes.replace(' ', '')) else 0
        
        # Estimated additional costs
        insurance = 800
        maintenance = 1000
        total_monthly_cost = monthly_payment + levies_num + rates_num + insurance + maintenance
        
        # Generate filename
        filename = self.generate_filename(property_data)
        
        # Generate dynamic amenities
        amenities_yaml = self.generate_dynamic_amenities_frontmatter(amenities, key_features)

        frontmatter = f"""---
date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
tags:
  - property
  - {location.lower().replace(' ', '_')}
cssclasses:
  - page-manila
  - pen-black
type: property
source: {property_data.get('source', 'Property24')}
url: {property_data.get('url', '')}
scraped_date: {property_data.get('scraped_date', '')}
title: {self.safe_string(title)}
property_type: {self.safe_string(overview.get('type_of_property', property_data.get('property_type', '')))}
price: {price}
currency: {property_data.get('currency', 'ZAR')}
date_posted: {property_data.get('date_posted', '')}
address: {self.safe_string(property_data.get('address', ''))}
area: {area}
location: {location}
province: {property_data.get('province', '')}
latitude: {property_data.get('latitude', '') or 'null'}
longitude: {property_data.get('longitude', '') or 'null'}
bedrooms: {key_features.get('bedrooms', property_data.get('bedrooms', 'null'))}
bathrooms: {key_features.get('bathrooms', property_data.get('bathrooms', 'null'))}
parking: {key_features.get('parking', 'null')}
size: {overview.get('floor_size', property_data.get('size', 'N/A'))}
agent_name: {self.safe_string(property_data.get('agent_name', ''))}
agency_name: {self.safe_string(property_data.get('agency_name', ''))}
listing_url: {property_data.get('listing_url', '')}
image_url: {property_data.get('image_url', '')}
status: interested
monthly_payment: {int(monthly_payment)}
total_monthly_cost: {int(total_monthly_cost)}
{amenities_yaml}
---
"""
        
        note_content = f"""{frontmatter}
# {title}

## Basic Information

| Field | Value |
|-------|-------|
| **Address** | {property_data.get('address', 'N/A')} |
| **Location** | [[{location}]] |
| **Property Type** | {overview.get('type_of_property', property_data.get('property_type', 'N/A'))} |
| **Lifestyle** | {overview.get('lifestyle', 'N/A')} |
| **Listing Number** | {overview.get('listing_number', 'N/A')} |
| **Listing Date** | {overview.get('listing_date', property_data.get('date_posted', 'N/A'))} |
| **Source** | [{property_data.get('source', 'N/A')}]({property_data.get('url', '')}) |

## Financial Analysis

### Purchase Price & Costs

| Item | Amount |
|------|--------|
| **Purchase Price** | {self.format_currency(price)} |
| **Transfer Duty** | {self.format_currency(transfer_duty)} |
| **Bond Registration** | R8,000 (est.) |
| **Transfer Costs** | R15,000 (est.) |
| **Attorney Fees** | R12,000 (est.) |
| **Bond Origination** | R6,000 (est.) |
| **Total Purchase Cost** | {self.format_currency(price + transfer_duty + 41000)} |

### Bond Calculations

| Item | Amount |
|------|--------|
| **Deposit (10%)** | {self.format_currency(deposit)} |
| **Bond Amount** | {self.format_currency(bond_amount)} |
| **Interest Rate** | 11.75% (prime) |
| **Bond Term** | 20 years |
| **Monthly Payment** | {self.format_currency(monthly_payment)} |
| **Bond to Value** | {(bond_amount/price*100):.1f}% |

### Monthly Costs

| Item | Amount |
|------|--------|
| **Bond Payment** | {self.format_currency(monthly_payment)} |
| **Levies** | {levies} |
| **Rates & Taxes** | {rates_taxes} |
| **Insurance** | {self.format_currency(insurance)} (est.) |
| **Maintenance** | {self.format_currency(maintenance)} (est.) |
| **Total Monthly** | {self.format_currency(total_monthly_cost)} |

### Investment Metrics

| Metric | Value |
|--------|-------|
| **Price per m²** | {overview.get('price_per_m²', 'N/A')} |
| **Transfer Duty Exempt** | {overview.get('no_transfer_duty', 'N/A')} |
| **Break-even Rental** | {self.format_currency(total_monthly_cost)} |

## Property Features

### Room Layout

| Room Type | Count | Details |
|-----------|-------|---------|
| **Bedrooms** | {key_features.get('bedrooms', rooms.get('bedrooms', 'N/A'))} | |
| **Bathrooms** | {key_features.get('bathrooms', rooms.get('bathrooms', 'N/A'))} | |
| **Parking** | {key_features.get('parking', external.get('parking', 'N/A'))} | {external.get('parking', '')} |

### Property Specifications

| Specification | Value |
|---------------|-------|
| **Floor Size** | {overview.get('floor_size', property_data.get('size', 'N/A'))} |
| **Erf Size** | {overview.get('erf_size', 'N/A')} |
| **Price per m²** | {overview.get('price_per_m²', 'N/A')} |
| **Levies** | {levies} |
| **Rates & Taxes** | {rates_taxes} |
| **Pets Allowed** | {overview.get('pets_allowed', property_data.get('pets_allowed', 'N/A'))} |
"""
        
        # Add key features dynamically
        if key_features:
            note_content += f"\n### Key Features\n\n"
            for feature, value in key_features.items():
                if isinstance(value, bool) and value:
                    note_content += f"- {feature.replace('_', ' ').title()}\n"
                elif not isinstance(value, bool):
                    note_content += f"- {feature.replace('_', ' ').title()}: {value}\n"

        # Add amenities dynamically
        if amenities:
            note_content += f"\n### Amenities\n\n"
            for amenity, present in amenities.items():
                if present:
                    note_content += f"- {amenity.replace('_', ' ').title()}\n"

        # Add external features
        if external:
            note_content += f"\n### External Features\n\n"
            for feature, detail in external.items():
                note_content += f"- {feature.replace('_', ' ').title()}: {detail}\n"

        note_content += f"""
## Location & Surroundings

### Address Details

- **Full Address**: {property_data.get('address', 'N/A')}
- **Area**: {area}
- **Province**: {property_data.get('province', 'N/A')}
- **GPS Coordinates**: {property_data.get('latitude', 'N/A')}, {property_data.get('longitude', 'N/A')}
"""
        
        # Add points of interest dynamically
        if poi:
            note_content += "### Points of Interest\n\\n"
            for category, items in poi.items():
                note_content += f"#### {category.replace('_', ' ').title()}\n"
                for item in items[:5]:  # Show first 5 items
                    note_content += f"- **{item['name']}** - {item['distance']}\n"
                if len(items) > 5:
                    note_content += f"- *...and {len(items) - 5} more*\n"
                note_content += "\n"

        note_content += f"""
## Agent Information

| Field | Value |
|-------|-------|
| **Agent Name** | {property_data.get('agent_name', 'N/A')} |
| **Agency** | {property_data.get('agency_name', 'N/A')} |
| **Contact** | |

## Property Description

{property_data.get('description', 'No description available.')}

## Viewing & Decision

### Viewing Details

- **Viewing Date**: 
- **Viewing Time**: 
- **Viewing Notes**: 

### Property Assessment

- **Overall Condition**: 
- **Score (1-10)**: 
- **Pros**: 
  - 
- **Cons**: 
  - 

### Decision Making

- **Decision**: 
- **Reason**: 
- **Next Steps**: 

## Documents & Links

### Required Documents

- [ ] Title Deed
- [ ] Rates Certificate
- [ ] Electrical Certificate
- [ ] Plumbing Certificate
- [ ] Building Plans
- [ ] Body Corporate Rules (if applicable)

### Links

- **Property Listing**: {property_data.get('url', 'N/A')}

---
*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Scraped from: {property_data.get('source', 'N/A')} on {property_data.get('scraped_date', 'N/A')}*
"""
        
        return {
            'filename': filename,
            'content': note_content,
            'location': location,
            'metadata': {
                'price': price,
                'location': location,
                'bedrooms': key_features.get('bedrooms', property_data.get('bedrooms', 'N/A')),
                'bathrooms': key_features.get('bathrooms', property_data.get('bathrooms', 'N/A')),
                'monthly_cost': int(total_monthly_cost)
            }
        }

