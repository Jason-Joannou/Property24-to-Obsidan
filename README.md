# Property24 Scraper & Obsidian Note Generator

A Python tool that scrapes Property24 listings and automatically generates organized Obsidian notes with financial analysis and property details.

## What it does

- Scrapes Property24 property listings
- Extracts property details, financial data, and location information
- Generates comprehensive Obsidian notes with financial calculations
- Organizes notes by Province → City → Suburb in your vault

## How to use it

1. **Setup**
   ```bash
   git clone https://github.com/Jason-Joannou/Property24-to-Obsidan.git
   cd property24-scraper
   pip install -r requirements.txt
   ```

2. **Configure**
   ```bash
   cp .env.example .env
   # Edit .env with your Obsidian vault path
   ```

3. **Run**
   ```python
   from scrapper.property_scrapper import PropertyScrapper
   from scrapper.obsidian_note_generator import PropertyNoteGenerator

   scraper = PropertyScrapper()
   note_generator = PropertyNoteGenerator()

   # Scrape and save
   property_data = scraper.scrape_property("https://www.property24.com/for-sale/...")
   note_result = note_generator.generate_obsidian_note(property_data)
   note_generator.save_note_to_obsidian(note_result)
   ```

## Example Output

The tool generates structured Obsidian notes like this:

```markdown
---
title: "2 Bedroom Apartment / flat for sale in Zonnebloem"
type: property
price: 1890000
bedrooms: 2
bathrooms: 1
suburb: Zonnebloem
tags: [property]
---

# 2 Bedroom Apartment / flat for sale in Zonnebloem

## Location & Basic Info
| Field | Value |
|-------|-------|
| **Address** | Chapel Towers, 123 Chapel Street |
| **Suburb** | [[Zonnebloem]] |
| **City** | Cape Town |
| **Province** | Western Cape |

## Financial Analysis
### Purchase Costs
| Item | Amount |
|------|--------|
| **Purchase Price** | R1,890,000 |
| **Transfer Duty** | R56,700 |
| **Total Purchase Cost** | R2,131,000 |

### Monthly Costs
| Item | Amount |
|------|--------|
| **Bond Payment** | R15,234 |
| **Levies** | R2,000 |
| **Total Monthly** | R18,844 |

## Property Features
- **Bedrooms**: 2
- **Bathrooms**: 1
- **Kitchens**: 1 (Laundry)
- **Parking**: Underground Parking
- Pet Friendly
- Pool

## Points of Interest
### Education
- **Chapel Street Primary** - 0.48km
- **Holy Cross RC Primary** - 0.70km

### Food and Entertainment  
- **De Goewerneur** - 0.70km
- **The Shack** - 0.86km
```

**File saved to**: `ObsidianVault/Properties/Western Cape/Cape Town/Zonnebloem/2_bedroom_apartment_114098915.md`

## Future Work

- **Command Line Interface**: Global CLI tool for easy usage from anywhere
- **Multiple Property Sites**: Support for Private Property, Seeff, etc.
- **Batch Processing**: Scrape multiple properties at once
- **Price Tracking**: Monitor property price changes over time

## Requirements

- Python 3.7+
- Obsidian vault
- Property24 URLs