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
            numbers = re.findall(r'[\\\\d,]+', amount.replace(' ', ''))
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
        return str(value).replace('"', "'").replace('\\\\n', ' ').strip()
    
    def calculate_transfer_duty(self, price):
        """Calculate South African transfer duty"""
        if not price or not str(price).replace(',', '').isdigit():
            return 0
        
        price_num = int(str(price).replace(',', ''))
        
        if price_num <= 1210000:
            return 0
        elif price_num <= 1663800:
            return (price_num - 1210000) * 0.03
        elif price_num <= 2329300:
            return 13614 + (price_num - 1663800) * 0.06
        elif price_num <= 2994800:
            return 53544 + (price_num - 2329300) * 0.08
        elif price_num <= 13310000:
            return 106784 + (price_num - 2994800) * 0.11
        else:
            return 1241456 + (price_num - 13310000) * 0.13
        
    def calculate_once_off_costs(self, price):
        """Estimate once-off costs as % of purchase price or loan amount"""
        deposit = price * 0.10
        transfer_duty = self.calculate_transfer_duty(price)
        bond_amount = price - deposit

        bond_registration = bond_amount * 0.01
        transfer_costs = price * 0.01
        attorney_fees = price * 0.005
        bond_origination = bond_amount * 0.005
        moving_costs = price * 0.002
        security_setup = price * 0.005
        immediate_repairs = price * 0.01  # 1%

        total_once_off = deposit + transfer_duty + bond_registration + transfer_costs + attorney_fees + bond_origination + moving_costs + security_setup + immediate_repairs

        return {
            'deposit': deposit,
            'transfer_duty': transfer_duty,
            'bond_registration': bond_registration,
            'transfer_costs': transfer_costs,
            'attorney_fees': attorney_fees,
            'bond_origination': bond_origination,
            'moving_costs': moving_costs,
            'security_setup': security_setup,
            'immediate_repairs': immediate_repairs,
            'total_once_off': total_once_off
        }

    def calculate_monthly_costs(self, bond_amount, levies, rates_taxes, price):
        """Estimate total monthly costs with scalable percentages"""

        monthly_payment = self.calculate_bond_payment(bond_amount)
        insurance = (bond_amount * 0.003) / 12  # ~0.3% annually
        maintenance = (price * 0.01) / 12       # ~1% annually

        # Utilities: estimate at 0.1% of property price per month, capped between R1500-R3500
        utilities = max(1500, min(price * 0.001, 3500))

        # Security: estimate at 0.02% of property price per month, capped between R300-R800
        security = max(300, min(price * 0.0002, 800))

        total_monthly = monthly_payment + levies + rates_taxes + insurance + maintenance + utilities + security

        return {
            'bond_payment': monthly_payment,
            'levies': levies,
            'rates_taxes': rates_taxes,
            'insurance': insurance,
            'maintenance': maintenance,
            'utilities': utilities,
            'security': security,
            'total_monthly': total_monthly
        }

        
    def generate_amenities_frontmatter(self, key_features):
        """Generate amenities section for frontmatter from key_features"""
        amenities_yaml = ""
        
        # Combine amenities from both sources
        all_amenities = set()  # Use set to avoid duplicates
        
        # Add amenities from text analysis
        if key_features:
            for amenity, present in key_features.items():
                if present:
                    all_amenities.add(amenity)
        
        # Generate YAML list for amenities
        if all_amenities:
            amenities_yaml = "amenities:\n"
            for amenity in sorted(all_amenities):
                amenities_yaml += f"  - {amenity}\n"
        
        return amenities_yaml.strip()
            
    def calculate_bond_payment(self, principal, rate=0.1075, years=20):
        """Calculate monthly bond payment"""
        if not principal or principal <= 0:
            return 0
        
        monthly_rate = rate / 12
        num_payments = years * 12
        
        if monthly_rate == 0:
            return principal / num_payments
        
        return principal * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
    
    def generate_filename(self, property_data):
        """Generate a clean filename for the property"""
        # Use listing_name if available, otherwise construct from address
        title = property_data.get('listing_name', 'Property')
        address = property_data.get('address', '')
        suburb = property_data.get('suburb', '')
        listing_id = property_data.get('listing_id', '')
        
        # Use listing_name as base, clean it up
        base_name = title
        
        # Clean the filename
        filename = re.sub(r'[^a-zA-Z0-9\\\\s]', '', base_name)
        filename = re.sub(r'\\\\s+', '_', filename.strip())
        filename = filename[:50]  # Limit length
        
        # Add listing ID for uniqueness
        if listing_id:
            filename = f"{filename}_{listing_id}"
        
        return f"{filename}.md"
    
    def extract_numeric_value(self, value):
        """Extract numeric value from string or return as is"""
        if isinstance(value, str):
            # Try to extract number
            numbers = re.findall(r'[\\\\d,]+', value.replace(' ', ''))
            if numbers:
                clean_number = numbers[0].replace(',', '')
                if clean_number.isdigit():
                    return int(clean_number)
        return value
    
    def generate_obsidian_note(self, property_data):
        """Generate comprehensive Obsidian note from scraped property data"""
        if not property_data:
            return None
        
        # Extract basic information using new structure
        title = property_data.get('listing_name', 'Unknown Property')
        price = int(property_data.get('price', 0)) if property_data.get('price') else 0
        
        # Get nested data
        property_overview = property_data.get('property_overview', {}).get('property_overview', {})
        rooms = property_data.get('property_overview', {}).get('rooms', {})
        external_features = property_data.get('property_overview', {}).get('external_features', {})
        poi = property_data.get('property_overview', {}).get('points_of_interest', {})
        key_features = property_data.get('key_features', {})
        agent_info = property_data.get('listing_organized_by', {})
        
        # Calculate financials
        deposit = price * 0.1
        bond_amount = price - deposit
        
        # Get monthly costs from property overview
        levies = self.extract_numeric_value(property_overview.get('levies', '0'))
        rates_taxes = self.extract_numeric_value(property_overview.get('rates_and_taxes', '0'))
        
        # Estimated additional costs
        once_off_costs = self.calculate_once_off_costs(price)
        total_monthly_costs = self.calculate_monthly_costs(
            bond_amount=bond_amount,
            levies=levies,
            rates_taxes=rates_taxes,
            price=price
        )
        
        
        # Generate filename
        filename = self.generate_filename(property_data)
        
        # Generate amenities for frontmatter
        amenities_yaml = self.generate_amenities_frontmatter(key_features)

        # Create clean frontmatter optimized for dataview
        frontmatter = f"""---
date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
tags:
  - property
  - portfolio
cssclasses:
  - page-manila
  - pen-black
property_type: {property_data.get('property_type', '')}
status: interested
source: {property_data.get('source', 'Property24')}
province: {property_data.get('province', '')}
city: {property_data.get('city', '')}
suburb: {property_data.get('suburb', '')}
bedrooms: {property_data.get('bedrooms', 'null')}
bathrooms: {property_data.get('bathrooms', 'null')}
{amenities_yaml}
---
"""
        
        note_content = f"""{frontmatter}

# {title}

## Location & Basic Info

| Field | Value |
|-------|-------|
| **Address** | {property_data.get('address', 'N/A')} |
| **Suburb** | [[{property_data.get('suburb', 'N/A')}]] |
| **City** | {property_data.get('city', 'N/A')} |
| **Province** | {property_data.get('province', 'N/A')} |
| **Property Type** | {property_data.get('property_type', 'N/A')} |
| **Lifestyle** | {property_overview.get('lifestyle', 'N/A')} |
| **Listing ID** | {property_data.get('listing_id', 'N/A')} |
| **Listed Date** | {property_data.get('listing_date', 'N/A')} |

## Financial Analysis

### Purchase Costs

| Item | Amount |
|------|--------|
| **Purchase Price** | {self.format_currency(price)} |
| **Deposit (10%)** | {self.format_currency(once_off_costs['deposit'])} |
| **Transfer Duty** | {self.format_currency(once_off_costs['transfer_duty'])} |
| **Bond Registration** | {self.format_currency(once_off_costs['bond_registration'])} |
| **Transfer Costs** | {self.format_currency(once_off_costs['transfer_costs'])} |
| **Attorney Fees** | {self.format_currency(once_off_costs['attorney_fees'])} |
| **Bond Origination** | {self.format_currency(once_off_costs['bond_origination'])} |
| **Moving Costs** | {self.format_currency(once_off_costs['moving_costs'])} |
| **Security Setup** | {self.format_currency(once_off_costs['security_setup'])} |
| **Immediate Repairs** | {self.format_currency(once_off_costs['immediate_repairs'])} |
| **Total Purchase Cost** | {self.format_currency(once_off_costs['total_once_off'])} |

### Bond Calculations

| Item | Amount |
|------|--------|
| **Deposit (10%)** | {self.format_currency(deposit)} |
| **Bond Amount** | {self.format_currency(bond_amount)} |
| **Interest Rate** | 10.75% (prime) |
| **Bond Term** | 20 years |
| **Monthly Payment** | {self.format_currency(total_monthly_costs['bond_payment'])} |

### Monthly Costs

| Item | Amount |
|------|--------|
| **Bond Payment** | {self.format_currency(total_monthly_costs['bond_payment'])} |
| **Levies** | {self.format_currency(total_monthly_costs['levies'])} |
| **Rates & Taxes** | {self.format_currency(total_monthly_costs['rates_taxes'])} |
| **Insurance** | {self.format_currency(total_monthly_costs['insurance'])} |
| **Maintenance** | {self.format_currency(total_monthly_costs['maintenance'])} |
| **Utilities** | {self.format_currency(total_monthly_costs['utilities'])} |
| **Security** | {self.format_currency(total_monthly_costs['security'])} |
| **Total Monthly** | {self.format_currency(total_monthly_costs['total_monthly'])} |

### Investment Metrics

| Metric | Value |
|--------|-------|
| **Price per m²** | R{property_overview.get('price_per_m2', 'N/A')} |
| **Transfer Duty Exempt** | {property_overview.get('no_transfer_duty', 'N/A')} |
| **Break-even Rental** | {self.format_currency(total_monthly_costs['total_monthly'])} |

## Property Features

### Room Layout

"""
        
        # Add rooms dynamically
        if rooms:
            for room_type, room_data in rooms.items():
                room_name = room_type.replace('_', ' ').title()
                if isinstance(room_data, list):
                    count = room_data[0] if room_data else 'N/A'
                    details = ', '.join(room_data[1:]) if len(room_data) > 1 else ''
                else:
                    count = room_data
                    details = ''
                note_content += f"- **{room_name}**: {count}"
                if details:
                    note_content += f" ({details})"
                note_content += "\n"
        
        note_content += f"""

### Property Specifications

| Specification | Value |
|---------------|-------|
| **Floor Size** | {property_data.get('floor_size', 'N/A')} m² |
| **Erf Size** | {property_overview.get('erf_size', 'N/A')} |
| **Levies** | {self.format_currency(levies)} |
| **Rates & Taxes** | {self.format_currency(rates_taxes)} |
| **Pets Allowed** | {property_data.get('allowed_pets', 'N/A')} |
"""

        # Add key features
        if key_features:
            note_content += "\n### Key Features\n"
            for feature, value in key_features.items():
                if isinstance(value, bool) and value:
                    note_content += f"- {feature.replace('_', ' ').title()}\n"
                elif not isinstance(value, bool) and value:
                    note_content += f"- **{feature.replace('_', ' ').title()}**: {value}\n"

        # Add external features
        if external_features:
            note_content += "\n### External Features\n"
            for feature, detail in external_features.items():
                note_content += f"- **{feature.replace('_', ' ').title()}**: {detail}\n"

        note_content += f"""

## Points of Interest
"""
        
        # Add points of interest
        if poi:
            for category, places in poi.items():
                if places:  # Only show categories with places
                    note_content += f"\n### {category.replace('_', ' ').title()}\n\n"
                    for place in places[:5]:  # Show first 5
                        note_content += f"- **{place['name']}** - {place['distance']}\n"
                    if len(places) > 5:
                        note_content += f"- *...and {len(places) - 5} more*\n"

        note_content += f"""

## Agent Information

| Field | Value |
|-------|-------|
| **Agent Name** | {agent_info.get('name', 'N/A')} |
| **Agency** | {agent_info.get('works_for', {}).get('name', 'N/A')} |
| **Agent Profile** | [{agent_info.get('name', 'View Profile')}]({agent_info.get('agent_url', '')}) |
| **Agency Profile** | [{agent_info.get('works_for', {}).get('name', 'View Agency')}]({agent_info.get('works_for', {}).get('works_for_url', '')}) |

## Viewing & Assessment

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

### Decision
- **Status**: 
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
- **Property Listing**: [View on Property24]({property_data.get('url', '')})
- **Property Images**: [View Images]({property_data.get('listing_image', '')})

---
*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*  
*Scraped from: {property_data.get('source', 'N/A')} on {property_data.get('scraped_date', 'N/A')}*
"""
        
        return {
            'filename': filename,
            'content': note_content,
            'location': property_data.get('suburb', 'Unknown'),
            'metadata': {
                'price': price,
                'location': property_data.get('suburb', 'Unknown'),
                'bedrooms': property_data.get('bedrooms', 'N/A'),
                'bathrooms': property_data.get('bathrooms', 'N/A'),
                'monthly_cost': int(total_monthly_costs['total_monthly'])
            }
        }