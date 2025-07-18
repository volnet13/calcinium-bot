import os
import math
import re
import ast
import operator
import sys
import logging
from flask import Flask, request
import telebot
from telebot import types

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required. Please set it in your hosting platform.")

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Flask app for webhook
app = Flask(__name__)

# Safer evaluation using AST
def safe_eval(expr):
    """Safely evaluate mathematical expressions using AST parsing"""
    
    # Normalize the expression - convert to lowercase for function names
    # but preserve case for constants
    expr = preprocess_expression(expr)
    
    # Allowed operators
    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    
    # Allowed functions
    allowed_functions = {
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'sqrt': math.sqrt,
        'log': math.log,
        'log10': math.log10,
        'exp': math.exp,
        'abs': abs,
        'round': round,
        'pow': pow,
        'ceil': math.ceil,
        'floor': math.floor,
        'factorial': math.factorial,
        'degrees': math.degrees,
        'radians': math.radians,
    }
    
    # Allowed constants
    allowed_names = {
        'pi': math.pi,
        'e': math.e,
    }
    
    def eval_node(node):
        if isinstance(node, ast.Constant):  # Numbers
            return node.value
        elif isinstance(node, ast.Name):  # Variables/constants
            if node.id in allowed_names:
                return allowed_names[node.id]
            else:
                raise ValueError(f"Name '{node.id}' not allowed")
        elif isinstance(node, ast.BinOp):  # Binary operations
            left = eval_node(node.left)
            right = eval_node(node.right)
            op = allowed_ops.get(type(node.op))
            if op is None:
                raise ValueError(f"Operator {type(node.op).__name__} not allowed")
            return op(left, right)
        elif isinstance(node, ast.UnaryOp):  # Unary operations
            operand = eval_node(node.operand)
            op = allowed_ops.get(type(node.op))
            if op is None:
                raise ValueError(f"Operator {type(node.op).__name__} not allowed")
            return op(operand)
        elif isinstance(node, ast.Call):  # Function calls
            if hasattr(node.func, 'id') and node.func.id in allowed_functions:
                args = [eval_node(arg) for arg in node.args]
                return allowed_functions[node.func.id](*args)
            else:
                func_name = getattr(node.func, 'id', 'unknown')
                raise ValueError(f"Function '{func_name}' not allowed")
        else:
            raise ValueError(f"Node type {type(node)} not allowed")
    
    try:
        # Parse the expression
        tree = ast.parse(expr, mode='eval')
        # Evaluate the parsed tree
        result = eval_node(tree.body)
        return result
    except Exception as e:
        raise ValueError(f"Invalid expression: {str(e)}")

def preprocess_expression(expr):
    """Preprocess expression to handle case sensitivity and operator normalization"""
    
    # Convert ** to pow() function calls for better compatibility
    expr = convert_power_operator(expr)
    
    # List of function names that should be lowercase
    function_names = [
        'sin', 'cos', 'tan', 'sqrt', 'log', 'log10', 'exp', 
        'abs', 'round', 'pow', 'ceil', 'floor', 'factorial', 
        'degrees', 'radians'
    ]
    
    # Make function names case-insensitive
    for func in function_names:
        # Replace case-insensitive function names with lowercase
        pattern = re.compile(re.escape(func), re.IGNORECASE)
        expr = pattern.sub(func, expr)
    
    # Make constants case-insensitive
    constants = {'pi': math.pi, 'e': math.e}
    for const in constants:
        pattern = re.compile(r'\b' + re.escape(const) + r'\b', re.IGNORECASE)
        expr = pattern.sub(const, expr)
    
    return expr

def convert_power_operator(expr):
    """Convert ** operator to pow() function calls"""
    # Simple regex to handle most cases of ** operator
    # This handles cases like: 2**3, (2+3)**4, x**y
    pattern = r'([a-zA-Z_][a-zA-Z0-9_]*|\d+(?:\.\d+)?|\([^)]+\))\s*\*\*\s*([a-zA-Z_][a-zA-Z0-9_]*|\d+(?:\.\d+)?|\([^)]+\))'
    
    def replace_power(match):
        base = match.group(1)
        exponent = match.group(2)
        return f'pow({base}, {exponent})'
    
    # Keep replacing until no more ** operators found
    prev_expr = None
    while prev_expr != expr:
        prev_expr = expr
        expr = re.sub(pattern, replace_power, expr)
    
    return expr

def is_math_expression(expr):
    """Check if the text looks like a mathematical expression"""
    
    # Skip if message is too long (likely not a math expression)
    if len(expr) > 100:
        return False
    
    # Must contain at least one digit or mathematical constant
    if not (any(char.isdigit() for char in expr) or 
            re.search(r'\b(pi|e)\b', expr.lower())):
        return False
    
    # Skip if it contains letters mixed with numbers in a non-mathematical way
    # This catches things like "work 24*7" or "available 24*7" but allows standalone "24*7"
    if re.search(r'[a-zA-Z]\s+\d+\s*[\*\+\-\/]\s*\d+', expr) or re.search(r'\d+\s*[\*\+\-\/]\s*\d+\s+[a-zA-Z]', expr):
        return False
    
    # Must be relatively short and focused
    words = expr.split()
    if len(words) > 5:  # If more than 5 words, likely not a math expression
        return False
    
    # Only ignore if it contains non-math words in a sentence context
    non_math_words = [
        'work', 'available', 'online', 'service', 'support', 'help',
        'hours', 'days', 'time', 'schedule', 'shift', 'open',
        'round', 'game', 'match', 'tournament', 'level', 'stage',
        'chapter', 'episode', 'season', 'day', 'week', 'month',
        'year', 'hour', 'minute', 'second', 'page', 'will', 'now',
        'step', 'phase', 'part', 'section', 'question', 'problem',
        'test', 'exam', 'quiz', 'lesson', 'class', 'grade',
        'score', 'point', 'goal', 'target', 'limit', 'max',
        'min', 'total', 'sum', 'count', 'number', 'amount',
        'price', 'cost', 'value', 'rate', 'percent', 'degree',
        'host', 'server', 'bot', 'it', 'this', 'that', 'the'
    ]
    
    # Check if expression contains non-math context words (only if more than 1 word)
    if len(words) > 1:
        for word in words:
            # Remove punctuation for word checking
            clean_word = re.sub(r'[^\w]', '', word.lower())
            if clean_word in non_math_words:
                return False
    
    # Must contain mathematical operators or functions or constants
    operator_patterns = [
        r'\d+\s*[\+\-\*/\^%]\s*\d+',  # Number operator number
        r'\([^)]*[\+\-\*/\^%\*\*][^)]*\)',  # Operations within parentheses
        r'\*\*',  # Power operator
    ]
    
    has_operator = any(re.search(pattern, expr) for pattern in operator_patterns)
    
    # OR must be a function call with parentheses
    function_patterns = [
        r'\bsin\s*\(', r'\bcos\s*\(', r'\btan\s*\(', r'\bsqrt\s*\(', 
        r'\blog\s*\(', r'\bexp\s*\(', r'\babs\s*\(', r'\bround\s*\(', 
        r'\bpow\s*\(', r'\bceil\s*\(', r'\bfloor\s*\(', 
        r'\bfactorial\s*\(', r'\bdegrees\s*\(', r'\bradians\s*\(', 
        r'\blog10\s*\('
    ]
    
    has_function = any(re.search(pattern, expr.lower()) for pattern in function_patterns)
    
    # OR contains mathematical constants
    has_constant = re.search(r'\b(pi|e)\b', expr.lower())
    
    return has_operator or has_function or has_constant

@bot.message_handler(commands=['start'])
def start_command(message):
    welcome_msg = (
        "🤖 *Welcome to Calcinium!*\n\n"
        "I'm your mathematical calculator bot. Send me any math expression and I'll solve it!\n\n"
        "Examples:\n"
        "• `2 + 2 * 5`\n"
        "• `sqrt(16) + pow(2, 3)`\n"
        "• `sin(pi/2) + cos(0)`\n"
        "• `log(e) + factorial(5)`\n"
        "• `2**3` (power operator)\n"
        "• `Pi/2` (case insensitive)\n\n"
        "Use /help for more information."
    )
    bot.reply_to(message, welcome_msg, parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def help_command(message):
    help_msg = (
        "🧠 *Calcinium Help*\n\n"
        "*Supported Operations:*\n"
        "• Basic: `+`, `-`, `*`, `/`, `**` (power), `%` (modulo)\n"
        "• Parentheses: `()` for grouping\n\n"
        "*Supported Functions:*\n"
        "• Trigonometric: `sin`, `cos`, `tan`\n"
        "• Logarithmic: `log`, `log10`, `exp`\n"
        "• Utility: `sqrt`, `abs`, `round`, `pow`\n"
        "• Advanced: `ceil`, `floor`, `factorial`, `degrees`, `radians`\n\n"
        "*Constants:*\n"
        "• `pi` (π ≈ 3.14159)\n"
        "• `e` (≈ 2.71828)\n\n"
        "*Features:*\n"
        "• Case insensitive functions: `Sin`, `COS`, `Factorial`\n"
        "• Power operator: `2**3` or `pow(2,3)`\n"
        "• Constants in expressions: `pi/2`, `e/2`\n\n"
        "*Examples:*\n"
        "• `2 + 2 * 5` → 12\n"
        "• `sqrt(16) + pow(2, 3)` → 12.0\n"
        "• `sin(pi/2)` → 1.0\n"
        "• `factorial(5)` → 120\n"
        "• `log(e)` → 1.0\n"
        "• `2**3` → 8\n"
        "• `Pi/4` → 0.7854\n\n"
        "Just send me any mathematical expression!"
    )
    bot.reply_to(message, help_msg, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_expression(message):
    expr = message.text.strip()
    
    # Check if it looks like a math expression
    if not is_math_expression(expr):
        return
    
    try:
        result = safe_eval(expr)
        
        # Format the result nicely
        if isinstance(result, float):
            if result.is_integer():
                result = int(result)
            else:
                result = round(result, 10)  # Avoid floating point precision issues
        
        response = (
            f"🔢 *Expression:* `{expr}`\n"
            f"🎯 *Result:* `{result}`"
        )
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except ZeroDivisionError:
        bot.reply_to(message, "❌ *Error:* Division by zero is not allowed!", parse_mode="Markdown")
    except ValueError as e:
        bot.reply_to(message, f"❌ *Error:* {str(e)}", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "❌ *Error:* Invalid mathematical expression. Use /help for examples.", parse_mode="Markdown")

# Webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'Bad Request', 400

# Health check route
@app.route('/health', methods=['GET'])
def health():
    return 'OK', 200

def main():
    """Main function to run the bot"""
    try:
        # Get webhook configuration
        webhook_url = os.environ.get("WEBHOOK_URL")
        port = int(os.environ.get("PORT", 10000))
        
        if webhook_url:
            # Production: Use webhooks
            logger.info(f"🌐 Setting up webhook: {webhook_url}/webhook")
            bot.remove_webhook()
            bot.set_webhook(url=f"{webhook_url}/webhook")
            
            # Set bot commands
            commands = [
                types.BotCommand("start", "Start the bot and see welcome message"),
                types.BotCommand("help", "Show help and available functions"),
            ]
            bot.set_my_commands(commands)
            
            logger.info(f"🚀 Starting webhook server on port {port}")
            app.run(host='0.0.0.0', port=port, debug=False)
        else:
            # Development: Use polling
            logger.info("🤖 Calcinium bot is running with polling...")
            bot.remove_webhook()
            bot.infinity_polling(none_stop=True)
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
