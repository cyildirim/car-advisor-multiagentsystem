"""
Price Fairness Agent
Checks whether the asking price is fair for the vehicle described.
"""
from google.adk.agents import Agent
import os

price_agent = Agent(
    name="price_fairness_agent",
    model=os.getenv("DEFAULT_MODEL"),
    description="Evaluates whether a used car asking price is fair based on make, model, year, mileage and condition.",
    instruction="""
You are an expert used car pricing analyst for the UK market.

Given a car listing (make, model, year, mileage, asking price, and any condition notes),
evaluate whether the price is FAIR, OVERPRICED, or UNDERPRICED.

Use your knowledge of:
- Typical depreciation curves for this make/model
- Current UK used car market trends
- How mileage affects value (standard benchmark: 10,000-12,000 miles/year)
- How service history, condition and extras affect value

""",
)
