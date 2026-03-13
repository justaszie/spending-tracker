import { addDays, subDays, format } from "date-fns";

export type TransactionType = "payment" | "transfer" | "fee";
export type Side = "debit" | "credit";
export type TransactionSource = "Sparkasse" | "Revolut" | "PayPal" | "Amex";

export interface Transaction {
  id: string;
  transaction_datetime: string;
  type: TransactionType;
  counterparty: string;
  orig_amount: number;
  orig_currency: string;
  side: Side;
  source: TransactionSource;
  eur_amount: number;
  manually_added: boolean;
  note: string | null;
  category: string | null;
  meal_type: string | null;
  dedup_key: string;
  user_id: string;
}

const CATEGORIES = [
  "Housing: Rent", "Housing: Mortgage", "Housing: Repairs",
  "Utilities: Electricity", "Utilities: Water", "Utilities: Internet", "Utilities: Phone",
  "Food: Groceries", "Food: Restaurants", "Food: Cafe", "Food: Fast Food",
  "Transport: Public Transport", "Transport: Fuel", "Transport: Parking", "Transport: Maintenance", "Transport: Uber/Lyft",
  "Shopping: Clothing", "Shopping: Electronics", "Shopping: Home Decor", "Shopping: Kitchenware",
  "Entertainment: Streaming", "Entertainment: Concerts", "Entertainment: Gaming", "Entertainment: Books",
  "Health: Medical", "Health: Dentist", "Health: Pharmacy", "Health: Gym",
  "Travel: Flights", "Travel: Accommodation", "Travel: Car Rental",
  "Education: Courses", "Education: Books",
  "Personal Care: Haircut", "Personal Care: Cosmetics",
  "Gifts & Donations", "Insurance: Health", "Insurance: Car", "Taxes"
];

const COUNTERPARTIES = [
  "REWE City", "DM Drogerie", "Lieferando", "Uber", "DB Vertrieb", 
  "Amazon Mktplc", "Netflix", "Spotify", "Aldi Süd", "Edeka", 
  "Starbucks", "Shell Station", "Apple Store", "Steam Games", 
  "Vattenfall", "Telekom Deutschland", "GymShark", "McFit", 
  "Airbnb", "Lufthansa", "Deutsche Bahn", "Zara", "Uniqlo", 
  "IKEA", "Saturn", "MediaMarkt", "Pharmacy Berlin"
];

const SOURCES: TransactionSource[] = ["Sparkasse", "Revolut", "PayPal", "Amex"];

function randomDate(start: Date, end: Date) {
  return new Date(start.getTime() + Math.random() * (end.getTime() - start.getTime()));
}

export function generateMockTransactions(count: number = 50): Transaction[] {
  const transactions: Transaction[] = [];
  const today = new Date();
  
  for (let i = 0; i < count; i++) {
    const isExpense = Math.random() > 0.1; // 90% expenses
    const amount = Math.random() * (isExpense ? 150 : 3000) + 5;
    const date = randomDate(subDays(today, 90), today);
    const counterparty = COUNTERPARTIES[Math.floor(Math.random() * COUNTERPARTIES.length)];
    
    // Randomly assign categories to some
    const hasCategory = Math.random() > 0.4;
    let category = null;
    
    if (hasCategory) {
      category = CATEGORIES[Math.floor(Math.random() * CATEGORIES.length)];
    }

    transactions.push({
      id: crypto.randomUUID(),
      transaction_datetime: date.toISOString(),
      type: isExpense ? "payment" : "transfer",
      counterparty: counterparty,
      orig_amount: parseFloat(amount.toFixed(2)),
      orig_currency: "EUR",
      side: isExpense ? "debit" : "credit",
      source: SOURCES[Math.floor(Math.random() * SOURCES.length)],
      eur_amount: parseFloat(amount.toFixed(2)),
      manually_added: Math.random() > 0.95,
      note: Math.random() > 0.8 ? "Keep receipt" : null,
      category: category,
      meal_type: null,
      dedup_key: crypto.randomUUID(),
      user_id: crypto.randomUUID(),
    });
  }
  
  return transactions.sort((a, b) => 
    new Date(b.transaction_datetime).getTime() - new Date(a.transaction_datetime).getTime()
  );
}

export const mockTransactions = generateMockTransactions(100);
export const categories = CATEGORIES;
