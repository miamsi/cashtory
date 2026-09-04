-- Create User Settings Table
CREATE TABLE user_settings (
    user_id UUID REFERENCES auth.users(id) PRIMARY KEY,
    daily_target NUMERIC DEFAULT 150000
);

-- Enable RLS and create policy
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage their own settings" ON user_settings FOR ALL USING (auth.uid() = user_id);
