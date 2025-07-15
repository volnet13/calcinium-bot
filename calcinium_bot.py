import os
import math
import re
import ast
import operator
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# Get bot token from environment variable
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required. Please set it in your hosting platform.")

# Safer evaluation using AST
def safe_eval(expr):
    """Safely evaluate mathematical expressions using AST parsing"""
    
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
            if node.func.id in allowed_functions:
                args = [eval_node(arg) for arg in node.args]
                return allowed_functions[node.func.id](*args)
            else:
                raise ValueError(f"Function '{node.func.id}' not allowed")
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

def is_math_expression(expr):
    """Check if the text looks like a mathematical expression"""
    # Must contain at least one digit
    if not any(char.isdigit() for char in expr):
        return False
    
    # Ignore if it contains common non-math words
    non_math_words = [
        'round', 'game', 'match', 'tournament', 'level', 'stage',
        'chapter', 'episode', 'season', 'day', 'week', 'month',
        'year', 'time', 'hour', 'minute', 'second', 'page',
        'step', 'phase', 'part', 'section', 'question', 'problem',
        'test', 'exam', 'quiz', 'lesson', 'class', 'grade',
        'score', 'point', 'goal', 'target', 'limit', 'max',
        'min', 'total', 'sum', 'count', 'number', 'amount',
        'price', 'cost', 'value', 'rate', 'percent', 'degree'
    ]
    
    # Check if expression contains non-math context words
    words = expr.lower().split()
    for word in words:
        # Remove punctuation for word checking
        clean_word = re.sub(r'[^\w]', '', word)
        if clean_word in non_math_words:
            return False
    
    # Must contain mathematical operators (not just functions)
    operator_patterns = [
        r'\+', r'-', r'\*', r'/', r'\*\*', r'%', r'=',
        r'\(.*\)',  # parentheses with content
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
    
    return has_operator or has_function

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "🤖 *Welcome to Calcinium!*\n\n"
        "I'm your mathematical calculator bot. Send me any math expression and I'll solve it!\n\n"
        "Examples:\n"
        "• `2 + 2 * 5`\n"
        "• `sqrt(16) + pow(2, 3)`\n"
        "• `sin(pi/2) + cos(0)`\n"
        "• `log(e) + factorial(5)`\n\n"
        "Use `/help` for more information."
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        "*Examples:*\n"
        "• `2 + 2 * 5` → 12\n"
        "• `sqrt(16) + pow(2, 3)` → 12.0\n"
        "• `sin(pi/2)` → 1.0\n"
        "• `factorial(5)` → 120\n"
        "• `log(e)` → 1.0\n\n"
        "Just send me any mathematical expression!"
    )
    await update.message.reply_text(help_msg, parse_mode="Markdown")

async def handle_expression(update: Update, context: ContextTypes.DEFAULT_TYPE):
    expr = update.message.text.strip()
    
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
        
        await update.message.reply_text(response, parse_mode="Markdown")
        
    except ZeroDivisionError:
        await update.message.reply_text(
            "❌ *Error:* Division by zero is not allowed!",
            parse_mode="Markdown"
        )
    except ValueError as e:
        await update.message.reply_text(
            f"❌ *Error:* {str(e)}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(
            "❌ *Error:* Invalid mathematical expression. Use `/help` for examples.",
            parse_mode="Markdown"
        )

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Set bot commands for the menu
    commands = [
        BotCommand("start", "Start the bot and see welcome message"),
        BotCommand("help", "Show help and available functions"),
    ]
    await app.bot.set_my_commands(commands)

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_expression))

    print("🤖 Calcinium bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
    
