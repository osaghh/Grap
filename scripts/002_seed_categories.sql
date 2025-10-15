-- Insert categories
INSERT INTO public.categories (name, slug, description, image_url) VALUES
  ('Men''s Shoes', 'mens-shoes', 'Classic and contemporary footwear for men', '/classic-men-s-leather-shoes.jpg'),
  ('Women''s Shoes', 'womens-shoes', 'Elegant and stylish shoes for women', '/vintage-leather-shoes-display.jpg'),
  ('Boots', 'boots', 'Durable and fashionable boots', '/classic-men-s-leather-shoes.jpg'),
  ('Sneakers', 'sneakers', 'Comfortable casual sneakers', '/classic-men-s-leather-shoes.jpg'),
  ('Formal Shoes', 'formal-shoes', 'Premium formal footwear', '/vintage-leather-shoes-display.jpg'),
  ('Casual Shoes', 'casual-shoes', 'Everyday comfortable shoes', '/classic-men-s-leather-shoes.jpg')
ON CONFLICT (slug) DO NOTHING;