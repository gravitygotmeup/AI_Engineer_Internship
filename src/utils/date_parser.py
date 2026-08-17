# src/utils/date_parser.py
# =======================
# Purpose: Universal date parser for all date formats
# Why: Sources use different date formats - need to normalize them all
# Strategy: Try multiple parsing approaches, handle relative dates

import re
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from dateutil import tz
from typing import Optional, Union
from loguru import logger

# Regular expressions for relative time patterns
RELATIVE_PATTERNS = [
    (r'(\d+)\s+seconds?\s+ago', 'seconds'),
    (r'(\d+)\s+minutes?\s+ago', 'minutes'),
    (r'(\d+)\s+hours?\s+ago', 'hours'),
    (r'(\d+)\s+days?\s+ago', 'days'),
    (r'(\d+)\s+weeks?\s+ago', 'weeks'),
    (r'(\d+)\s+months?\s+ago', 'months'),
    (r'(\d+)\s+years?\s+ago', 'years'),
    (r'just\s+now', 'now'),
    (r'a\s+minute\s+ago', 'minute'),
    (r'an?\s+hour\s+ago', 'hour'),
    (r'yesterday', 'yesterday'),
    (r'today', 'today'),
]

def parse_relative_date(text: str) -> Optional[datetime]:
    """
    Parse relative dates like "2 hours ago", "yesterday", etc.
    
    Args:
        text: Relative date string
    
    Returns:
        Parsed datetime or None
    """
    if not text:
        return None
    
    text = text.lower().strip()
    
    # Check for "just now" 
    if 'just now' in text:
        return datetime.now()
    
    # Check for "today"
    if 'today' in text:
        return datetime.now()
    
    # Check for "yesterday"
    if 'yesterday' in text:
        return datetime.now() - timedelta(days=1)
    
    # Check for "tomorrow" (less common in news)
    if 'tomorrow' in text:
        return datetime.now() + timedelta(days=1)
    
    # Check for relative time patterns
    for pattern, unit in RELATIVE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            try:
                value = int(match.group(1)) if match.groups() else 1
                
                if unit == 'seconds':
                    return datetime.now() - timedelta(seconds=value)
                elif unit == 'minutes':
                    return datetime.now() - timedelta(minutes=value)
                elif unit == 'hours':
                    return datetime.now() - timedelta(hours=value)
                elif unit == 'days':
                    return datetime.now() - timedelta(days=value)
                elif unit == 'weeks':
                    return datetime.now() - timedelta(weeks=value)
                elif unit == 'months':
                    return datetime.now() - timedelta(days=value * 30)
                elif unit == 'years':
                    return datetime.now() - timedelta(days=value * 365)
                elif unit in ['now', 'minute', 'hour']:
                    if unit == 'minute' or unit == 'a minute':
                        return datetime.now() - timedelta(minutes=1)
                    elif unit == 'hour' or unit == 'an hour':
                        return datetime.now() - timedelta(hours=1)
                    return datetime.now()
            except Exception as e:
                logger.error(f"Error parsing relative date '{text}': {e}")
                continue
    
    return None

def parse_date(date_string: Union[str, None]) -> Optional[datetime]:
    """
    Universal date parser that handles multiple formats
    
    Args:
        date_string: Date string in any format
    
    Returns:
        Parsed datetime or None if parsing fails
    """
    if not date_string:
        return None
    
    # Clean up the string
    date_string = date_string.strip()
    
    # Try relative date parsing first
    relative_date = parse_relative_date(date_string)
    if relative_date:
        return relative_date
    
    # Try standard date parsing
    try:
        # Try to parse with dateutil
        parsed = date_parser.parse(date_string, fuzzy=True)
        
        # Check if parsed date is in the future (might be timezone issue)
        if parsed and parsed > datetime.now() + timedelta(days=1):
            # If the date is in the future, it might be a year parsing issue
            # Try to adjust year (sometimes 2024 gets parsed as 2025, etc.)
            try:
                # Try parsing with year adjustment
                parsed = date_parser.parse(date_string, fuzzy=True, default=datetime.now())
            except:
                pass
        
        return parsed
        
    except Exception as e:
        # Try more specific formats
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d %H:%M:%S.%f',
            '%B %d, %Y',
            '%b %d, %Y',
            '%d %B %Y',
            '%d %b %Y',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%d-%m-%Y',
            '%m-%d-%Y',
            '%Y/%m/%d',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_string, fmt)
            except:
                continue
        
        logger.debug(f"Could not parse date: {date_string}")
        return None

def is_within_last_24h(date_to_check: datetime) -> bool:
    """
    Check if a datetime is within the last 24 hours
    
    Args:
        date_to_check: Datetime to check
    
    Returns:
        True if within last 24 hours
    """
    if not date_to_check:
        return False
    
    now = datetime.now()
    diff = now - date_to_check
    return diff.total_seconds() <= 24 * 60 * 60  # 24 hours in seconds

def format_iso(date: datetime) -> str:
    """
    Format datetime as ISO-8601 string
    
    Args:
        date: Datetime to format
    
    Returns:
        ISO-8601 formatted string
    """
    if not date:
        return ''
    
    return date.isoformat()

# Example usage:
# from src.utils.date_parser import parse_date, is_within_last_24h
# 
# dates = [
#     "2 hours ago",
#     "2026-08-14T10:30:00Z",
#     "August 14, 2026",
#     "yesterday",
#     "just now"
# ]
# 
# for date_str in dates:
#     parsed = parse_date(date_str)
#     print(f"{date_str} -> {parsed}")