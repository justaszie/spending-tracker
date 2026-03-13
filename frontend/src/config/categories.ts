export const STANDARD_CATEGORY_LABELS: Record<string, string> = {
  BEAUTY_PRODUCTS: "Beauty products",
  CAFE_SNACKS: "Cafe & snacks",
  CONFERENCES: "Conferences",
  DRINKS: "Drinks",
  EATING_OUT: "Eating out",
  FOOD_DELIVERY: "Food delivery",
  GIFTS: "Gifts",
  GROCERIES: "Groceries",
  GYM: "Gym",
  HAIRCUTS: "Haircuts",
  HEALTH_INSURANCE: "Health insurance",
  HOBBIES: "Hobbies",
  HYGIENE: "Hygiene",
  MEDICAL: "Medical",
  MOBILE_PLANS: "Mobile plans",
  ONLINE_COURSES: "Online courses",
  OTHER: "Other",
  PERSONAL_TRAINING: "Personal training",
  RENT: "Rent",
  RENT_UTILITIES: "Rent - utilities",
  SHOPPING_CLOTHES: "Shopping - clothes",
  SHOPPING_OTHER: "Shopping - other",
  SOFTWARE_MONTHLY: "Software – monthly",
  SOFTWARE_YEARLY: "Software – yearly",
  STREAMING_SERVICES: "Streaming services",
  SUPPLEMENTS: "Supplements",
  TAXI: "Taxi",
  TICKETS_TO_EVENTS: "Tickets to events",
  TRANSPORT_CITY: "City transport",
  TRANSPORT_INTERCITY: "Intercity transport",
  TRAVEL_HOUSING: "Travel – housing",
  TRAVEL_OTHER: "Travel – other",
  TRAVEL_TRANSPORT: "Travel – transport",
};

export function getCategoryLabel(code: string): string {
  const trimmed = code?.trim();
  if (!trimmed) {
    return "";
  }

  return STANDARD_CATEGORY_LABELS[trimmed] ?? (trimmed[0].toUpperCase() + trimmed.toLowerCase().slice(1));
}