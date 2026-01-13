"""
Tool definitions for the Ticket Triage orchestrator.
"""

from typing import Optional
from langchain_core.tools import tool

# Placeholder for ORDERS data - will be loaded from mock_data
ORDERS: list[dict] = []


def load_orders(orders_data: list[dict]) -> None:
    """Load orders data into the module."""
    global ORDERS
    ORDERS = orders_data


@tool
def fetch_order(order_id: str) -> Optional[dict]:
    """
    Fetch order details by order ID.
    
    Args:
        order_id: The order ID to look up (e.g., "ORD1001").
        
    Returns:
        Order details as a dictionary, or None if not found.
    """
    for order in ORDERS:
        if order["order_id"] == order_id:
            return order
    return None


@tool
def search_orders(email: str) -> list[dict]:
    """
    Search orders by customer email.
    
    Args:
        email: The customer email to search for.
        
    Returns:
        List of orders matching the email (case-insensitive).
    """
    return [o for o in ORDERS if o["email"].lower() == email.lower()]


# List of tools available for the agent
tools = [fetch_order, search_orders]
