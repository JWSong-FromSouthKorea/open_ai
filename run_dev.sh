brew_services_list=$(brew services list)

if echo "$brew_services_list" | grep -q "mysql.*started"; then
  python main.py
else
  brew services start mysql
  python main.py
fi