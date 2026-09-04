-- 1. Create Wallets Table
CREATE TABLE wallets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    balance NUMERIC NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 2. Create Envelopes Table
CREATE TABLE envelopes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    month_year TEXT NOT NULL,
    name TEXT NOT NULL,
    planned_amount NUMERIC NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 3. Create Transactions Table
CREATE TABLE transactions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    type TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    source_wallet TEXT,
    destination_wallet TEXT,
    envelope TEXT,
    receivable_person TEXT,
    description TEXT,
    buffer_adjustment NUMERIC DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 4. Enable Row Level Security (RLS)
ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE envelopes ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

-- 5. Create Security Policies (Allows the app to read/write based on user_id)
CREATE POLICY "Users can manage their own wallets" 
ON wallets FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own envelopes" 
ON envelopes FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own transactions" 
ON transactions FOR ALL USING (auth.uid() = user_id);
