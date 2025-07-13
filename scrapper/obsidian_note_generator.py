import re
import json
from datetime import datetime
from typing import Dict
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class PropertyNoteGenerator:

    def __init__(self) -> None:
        self.vault_directory = os.getenv("VAULT_DIRECTORY")
        self.property_directory = os.getenv("PROPERTY_DIRECTORY")
        self.full_path = self._validate_vault_directory(os.path.join(self.vault_directory, self.property_directory))

    def _validate_vault_directory(self, directory):
        """Validates the vault directory and raises an exception if it does not exist

        Args:
            directory (str): The vault directory to validate

        Returns:
            str: The validated vault directory
        """
        directory = os.path.normpath(directory)
        if not os.path.exists(directory):
            raise Exception(f"Vault directory {directory} does not exist. Please create it and try again.")
        return directory

    def format_currency(self, amount):
        """Formats a currency amount for display in a note
    
        Args:
            amount (Union[str, int, float]): The amount to format
    
        Returns:
            str: The formatted amount, e.g. "R27,000"
        """
        if not amount:
            return "R0"
        
        # Handle string amounts like "R 27 000"
        if isinstance(amount, str):
            numbers = re.findall(r'[\\\\d,]+', amount.replace(' ', ''))
            if numbers:
                clean_amount = numbers[0].replace(',', '')
                if clean_amount.isdigit():
                    return f"R{int(clean_amount):,}"
            return amount
        
        if isinstance(amount, (int, float)):
            return f"R{int(amount):,}"
        
        return str(amount)
    
    
    def calculate_transfer_duty(self, price):
        """
        Calculate the transfer duty based on the property price.

        The transfer duty is calculated using a tiered system where different
        portions of the property's price are taxed at different rates.

        Args:
            price (Union[str, int]): The price of the property.

        Returns:
            float: The calculated transfer duty. Returns 0 if the price is invalid
            or below the minimum threshold for transfer duty.
        """

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
        """Calculate all the once-off costs associated with buying a property

        This includes the deposit, transfer duty, bond registration, transfer costs, attorney fees, bond origination, moving costs, security setup, and immediate repairs.

        Args:
            price (int): The price of the property

        Returns:
            dict: A dictionary containing all the calculated costs
        """
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

        additioanl_total_once_off_costs = deposit + transfer_duty + bond_registration + transfer_costs + attorney_fees + bond_origination + moving_costs + security_setup + immediate_repairs
        grand_total = price + additioanl_total_once_off_costs

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
            'additional_total_once_off': additioanl_total_once_off_costs,
            'grand_total': grand_total
        }

    def calculate_monthly_costs(self, bond_amount, levies, rates_taxes, price):
        """
        Calculate the monthly costs associated with owning a property.

        This includes the bond payment, levies, rates and taxes, insurance, maintenance, utilities, 
        and security costs. Estimates for utilities and security are capped within specified ranges.

        Args:
            bond_amount (float): The outstanding bond amount.
            levies (float): The monthly levies for the property.
            rates_taxes (float): The monthly rates and taxes for the property.
            price (float): The purchase price of the property.

        Returns:
            dict: A dictionary containing detailed breakdown of monthly costs, including:
                - 'bond_payment': Monthly bond payment.
                - 'levies': Monthly levies.
                - 'rates_taxes': Monthly rates and taxes.
                - 'insurance': Monthly insurance cost.
                - 'maintenance': Monthly maintenance cost.
                - 'utilities': Estimated monthly utilities cost.
                - 'security': Estimated monthly security cost.
                - 'total_monthly': Total monthly cost including all components.
        """

        monthly_payment = self.calculate_bond_payment(bond_amount)
        insurance = (bond_amount * 0.003) / 12  # ~0.3% annually
        maintenance = (price * 0.01) / 12       # ~1% annually

        # Utilities: estimate at 0.1% of property price per month, capped between R1500-R3500
        utilities = max(1500, min(price * 0.001, 3500))

        # Security: estimate at 0.02% of property price per month, capped between R300-R800
        security = max(300, min(price * 0.0002, 800))
        levies = self.extract_numeric_value(levies)
        rates_taxes = self.extract_numeric_value(rates_taxes)

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
        """
        Generate YAML frontmatter for amenities based on key_features.

        Args:
            key_features (dict): The key features extracted from the property listing.

        Returns:
            str: YAML frontmatter for amenities.
        """
        amenities_yaml = ""
        
        all_amenities = set()
        
        if key_features:
            for amenity, present in key_features.items():
                if present:
                    all_amenities.add(amenity)
        
        if all_amenities:
            amenities_yaml = "amenities:\n"
            for amenity in sorted(all_amenities):
                amenities_yaml += f"  - {amenity}\n"
        
        return amenities_yaml.strip()
            
    def calculate_bond_payment(self, principal, rate=0.1075, years=20):
        """
        Calculate the monthly bond payment for a given principal amount, interest rate, and repayment term.

        Args:
            principal (float): The outstanding bond amount.
            rate (float, optional): The interest rate as a decimal. Defaults to 0.1075 (10.75%).
            years (int, optional): The repayment term in years. Defaults to 20.

        Returns:
            float: The monthly bond payment amount.
        """
        if not principal or principal <= 0:
            return 0
        
        monthly_rate = rate / 12
        num_payments = years * 12
        
        if monthly_rate == 0:
            return principal / num_payments
        
        return principal * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
    
    def generate_filename(self, property_data):
        """
        Generate a filename for the Obsidian note based on the property data

        Uses the suburb and listing ID to create a unique filename. If no listing
        ID is provided, uses the current timestamp instead.

        Args:
            property_data (dict): The property data to generate a filename for

        Returns:
            str: The generated filename
        """
        suburb = property_data.get('suburb', 'property').lower()
        listing_id = property_data.get('listing_id', '')
        
        if listing_id:
            filename = f"{suburb}_{listing_id}"
        else:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{suburb}_{timestamp}"
        
        return f"{filename}.md"
    
    def extract_numeric_value(self, value):
        """Extract numeric value from string or return 0 if invalid"""
        if value is None:
            return 0.0

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            clean = value.replace(',', '').replace('R', '').replace('$', '').strip()
            try:
                return float(clean)
            except ValueError:
                pass

        return 0.0
    
    def generate_obsidian_note(self, property_data):
        """
        Generate an Obsidian note for a given property data.

        Args:
            property_data (dict): The property data to generate a note for.

        Returns:
            dict: A dictionary containing the filename, content, and geography data for the generated note.
        """
    
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
  - page-grid
  - pen-blue
  - page-white
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
| **Suburb** | {property_data.get('suburb', 'N/A')} |
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
| **Total Additional Once Off Cost** | {self.format_currency(once_off_costs['additional_total_once_off'])} |
| **Grand Total Once Off Cost** | {self.format_currency(once_off_costs['grand_total'])} |

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
| **Price per m2** | {self.format_currency(property_overview.get('price_per_m2', None))} |
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
| **Floor Size** | {property_data.get('floor_size', 'N/A')} m2 |
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
            'geography': {
                'province': property_data.get('province', None),
                'city': property_data.get('city', None),
                'suburb': property_data.get('suburb', None)
            }
        }
    
    def save_note_to_obsidian(self, note_data: Dict):
        """Save note data to a new note in the specified directory"""
        property_geography = note_data['geography']
        province = property_geography['province']
        city = property_geography['city']
        suburb = property_geography['suburb']

        if not province:
            property_folder = "Other"
        elif not city:
            property_folder = province
        elif not suburb:
            property_folder = os.path.join(province, city)
        else:
            property_folder = os.path.join(province, city, suburb)

        property_directory = os.path.join(self.full_path, property_folder)
        os.makedirs(property_directory, exist_ok=True)

        filepath = os.path.join(property_directory, note_data['filename'])
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(note_data['content'])
        
