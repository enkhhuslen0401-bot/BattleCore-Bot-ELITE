import os
import random
import asyncio
import time
import discord
from discord.ext import commands
from flask import Flask
import threading

# --- RENDER УНТАХААС СЭРГИЙЛЭХ ВЭБ СЕРВЕР ---
app = Flask("")

@app.route("/")
def home():
    return "Economy Bot is alive and running!"

def run_web():
    app.run(host="0.0.0.0", port=8080)

# Flask сервер ботын хажуугаар зэрэг ажиллана
threading.Thread(target=run_web).start()

# --- DISCORD BOT ТОХИРГОО ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Өгөгдөл хадгалах сан
users_data = {}
mayor_data = {"id": None, "treasury": 0}

# Level 1-10 хүртэлх ажил / тушаал
JOBS = {
    1: "Хог цэвэрлэгч 🗑️",
    2: "Худалдагч 🛒",
    3: "Бармен 🍹",
    4: "Хүргэлтийн ажилтан 🛵",
    5: "Ахлах Менежер 📊",
    6: "Программист 💻",
    7: "Бизнесмэн 💼",
    8: "Директор 🏢",
    9: "Сайд 🏛️",
    10: "Хотын Ерөнхийлөгч / Магнат 👑"
}

@bot.event
async def on_ready():
    print(f"Боть амжилттай холбогдлоо: {bot.user.name}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = str(message.author.id)
    if user_id not in users_data:
        users_data[user_id] = {
            "coins": 100, 
            "level": 1, 
            "exp": 0, 
            "energy": 100, 
            "inventory": [],
            "protection": False,
            "last_daily": 0
        }

    # Идэвхтэй байхад EXP нэмэгдэж, энергийг бага зэрэг хасна
    users_data[user_id]["exp"] += 15
    users_data[user_id]["energy"] = max(0, users_data[user_id]["energy"] - 1)

    # Level Up систем
    current_level = users_data[user_id]["level"]
    if users_data[user_id]["exp"] >= current_level * 100 and current_level < 10:
        users_data[user_id]["level"] += 1
        users_data[user_id]["exp"] = 0
        users_data[user_id]["coins"] += 150
        new_job = JOBS.get(users_data[user_id]["level"], "Магнат")
        await message.channel.send(f"🎉 **{message.author.name}** Level up! **Level {users_data[user_id]['level']}** болж дэвжлээ! Шинэ ажил: **{new_job}**! (+150 coins)")

    await bot.process_commands(message)

# ------------------ ХОТЫН ДАРГА & САНГИЙН СИСТЕМ ------------------

@bot.command(name="setmayor")
async def setmayor(ctx, member: discord.Member = None):
    global mayor_data
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Энэ команд зөвхөн админд зориулагдсан.")
        return

    if member is None:
        member = ctx.author

    mayor_data["id"] = str(member.id)
    await ctx.send(f"👑 **{member.name}** албан ёсоор Хотын Дарга (Mayor) боллоо!")

@bot.command(name="treasury", aliases=["bank"])
async def treasury(ctx):
    await ctx.send(f"🏛️ Хотын даргын сангийн үлдэгдэл: **${mayor_data['treasury']} коин**")

@bot.command(name="grant")
async def grant(ctx, member: discord.Member, amount: int):
    global mayor_data
    if str(ctx.author.id) != mayor_data["id"] and not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Энэ команд зөвхөн Хотын Даргад зориулагдсан.")
        return

    if mayor_data["treasury"] < amount:
        await ctx.send(f"❌ Санд мөнгө хүрэхгүй байна! (Үлдэгдэл: ${mayor_data['treasury']})")
        return

    mayor_data["treasury"] -= amount
    target_id = str(member.id)
    if target_id not in users_data:
        users_data[target_id] = {"coins": 100, "level": 1, "exp": 0, "energy": 100, "inventory": [], "protection": False, "last_daily": 0}

    users_data[target_id]["coins"] += amount
    await ctx.send(f"👑 Хотын дарга санваасаа **{member.name}**-д **${amount}** шагнал олголоо!")

# ------------------ ПРОФАЙЛ, ЭНЕРГИ & АЖИЛ ------------------

@bot.command(name="profile", aliases=["bal", "wallet"])
async def profile(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    
    user_id = str(member.id)
    if user_id not in users_data:
        users_data[user_id] = {"coins": 100, "level": 1, "exp": 0, "energy": 100, "inventory": [], "protection": False, "last_daily": 0}
    
    data = users_data[user_id]
    current_job = JOBS.get(data['level'], "Магнат")
    
    embed = discord.Embed(
        title=f"👤 {member.name}-ийн Профайл",
        color=discord.Color.green()
    )
    embed.add_field(name="🪙 Коин", value=f"${data['coins']}", inline=True)
    embed.add_field(name="📊 Level", value=f"Level {data['level']} (EXP: {data['exp']}/{data['level']*100})", inline=True)
    embed.add_field(name="⚡ Энерги", value=f"{data['energy']}/100", inline=True)
    embed.add_field(name="💼 Тушаал / Ажил", value=current_job, inline=True)
    embed.add_field(name="🛡️ Хамгаалалт", value="Идэвхтэй" if data['protection'] else "Үгүй", inline=True)
    embed.add_field(name="🎒 Цүнх (Inventory)", value=", ".join(data['inventory']) if data['inventory'] else "Хоосон", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="eat")
async def eat(ctx, food_type: str = None):
    user_id = str(ctx.author.id)
    if user_id not in users_data:
        users_data[user_id] = {"coins": 100, "level": 1, "exp": 0, "energy": 100, "inventory": [], "protection": False, "last_daily": 0}

    foods = {
        "apple": {"price": 10, "energy": 20, "name": "Алим 🍎"},
        "burger": {"price": 30, "energy": 50, "name": "Бургер 🍔"},
        "pizza": {"price": 50, "energy": 100, "name": "Пицца 🍕"}
    }

    if food_type is None or food_type.lower() not in foods:
        embed = discord.Embed(title="🍔 Хоолны Цэс", color=discord.Color.orange())
        embed.add_field(name="1. Алим 🍎 (`!eat apple`)", value="Үнэ: $10 | +20 Энерги", inline=False)
        embed.add_field(name="2. Бургер 🍔 (`!eat burger`)", value="Үнэ: $30 | +50 Энерги", inline=False)
        embed.add_field(name="3. Пицца 🍕 (`!eat pizza`)", value="Үнэ: $50 | +100 Энерги", inline=False)
        await ctx.send(embed=embed)
        return

    item = foods[food_type.lower()]
    if users_data[user_id]["coins"] < item["price"]:
        await ctx.send(f"❌ Танд {item['name']} авахад мөнгө хүрэлцэхгүй байна! (Үнэ: ${item['price']})")
        return

    users_data[user_id]["coins"] -= item["price"]
    users_data[user_id]["energy"] = min(100, users_data[user_id]["energy"] + item["energy"])
    await ctx.send(f"😋 **{ctx.author.name}** {item['name']} идэж энергээ **+{item['energy']}** сэргээлээ! (Энерги: {users_data[user_id]['energy']}/100)")

@bot.command(name="work")
async def work(ctx):
    user_id = str(ctx.author.id)
    if user_id not in users_data:
        users_data[user_id] = {"coins": 100, "level": 1, "exp": 0, "energy": 100, "inventory": [], "protection": False, "last_daily": 0}

    if users_data[user_id]["energy"] < 20:
        await ctx.send("❌ Таны энерги хэт бага байна! `!eat` гэж хоол идэж энергиэ сэргээнэ үү.")
        return

    users_data[user_id]["energy"] -= 20
    
    level = users_data[user_id]["level"]
    base_earn = random.randint(40, 90) * level
    current_job = JOBS.get(level, "Магнат")

    tax = int(base_earn * 0.10)
    net_earned = base_earn - tax
    
    users_data[user_id]["coins"] += net_earned
    mayor_data["treasury"] += tax

    await ctx.send(f"💼 Та **{current_job}** түвшингээр ажиллаад **${base_earn}** оллоо! (10% татвар ${tax} Хотын сан руу орж, гар дээр: **${net_earned}** авлаа)")

# ------------------ ӨДРИЙН УРАМШУУЛАЛ (!DAILY) ------------------

@bot.command(name="daily")
async def daily(ctx):
    user_id = str(ctx.author.id)
    current_time = int(time.time())
    
    if user_id not in users_data:
        users_data[user_id] = {"coins": 100, "level": 1, "exp": 0, "energy": 100, "inventory": [], "protection": False, "last_daily": 0}
    
    if "last_daily" not in users_data[user_id]:
        users_data[user_id]["last_daily"] = 0

    last_claim = users_data[user_id]["last_daily"]
    cooldown = 86400  # 24 цаг
    
    if current_time - last_claim < cooldown:
        remaining = cooldown - (current_time - last_claim)
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        await ctx.send(f"⏳ {ctx.author.mention}, та өдрийн урамшууллаа аль хэдийн авсан байна! Дахин авах хүртэл **{hours} цаг {minutes} минут** хүлээгээрэй.")
        return

    reward = 500
    users_data[user_id]["coins"] += reward
    users_data[user_id]["last_daily"] = current_time
    
    await ctx.send(f"🎉 {ctx.author.mention}, амжилттай өдрийн урамшуулал болох **{reward} коин** авлаа! Маргааш дахин аваарай.")

# ------------------ МИНИ ТОГЛООМУУД & ЭДИЙН ЗАСАГ ------------------

@bot.command(name="cf")
async def coinflip(ctx, amount: int, choice: str = None):
    if choice is None:
        await ctx.send("❌ Буруу формат! `!cf <дүн> <h эсвэл f>` гэж бичнэ үү.")
        return
        
    choice = choice.lower()
    if choice in ["h", "heads", "сулд", "сүлд"]:
        user_choice = "h"
    elif choice in ["f", "tails", "тоо"]:
        user_choice = "f"
    else:
        await ctx.send("❌ Зөвхөн `h` (Heads/Сүлд) эсвэл `f` (Tails/Тоо) сонгоно уу!")
        return
    
    result = random.choice(["h", "f"])
    
    if user_choice == result:
        await ctx.send(f"🎉 Зоос буулаа: **{result.upper()}**! Баяр хүргэе, та {amount} зоос хожлоо!")
    else:
        await ctx.send(f"😢 Зоос буулаа: **{result.upper()}**! Харамсалтай нь та {amount} зоос алдлаа.")

@bot.command(name="pay")
async def pay(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("❌ Шилжүүлэх дүн буруу байна.")
        return

    sender_id = str(ctx.author.id)
    receiver_id = str(member.id)

    if users_data.get(sender_id, {}).get("coins", 0) < amount:
        await ctx.send("❌ Таны хэтэвч хүрэлцэхгүй байна.")
        return

    tax = int(amount * 0.03)
    final_amount = amount - tax

    users_data[sender_id]["coins"] -= amount
    
    if receiver_id not in users_data:
        users_data[receiver_id] = {"coins": 100, "level": 1, "exp": 0, "energy": 100, "inventory": [], "protection": False, "last_daily": 0}
    
    users_data[receiver_id]["coins"] += final_amount
    mayor_data["treasury"] += tax

    await ctx.send(f"💸 **{ctx.author.name}** -> **{member.name}** руу **${final_amount}** шилжүүллээ (3% татвар ${tax} сан руу оролцов).")

@bot.command(name="rob")
async def rob(ctx, member: discord.Member):
    robber_id = str(ctx.author.id)
    target_id = str(member.id)

    if robber_id not in users_data or users_data[robber_id]["coins"] < 200:
        await ctx.send("❌ Дээрэм хийхийн тулд дор хаяж $200 коин хэрэгтэй.")
        return

    if users_data.get(target_id, {}).get("protection", False):
        await ctx.send(f"🛡️ **{member.name}** хулгайнаас хамгаалах системтэй тул дээрэмдэж чадсангүй!")
        return

    if users_data.get(target_id, {}).get("coins", 0) < 50:
        await ctx.send(f"❌ **{member.name}**-д дээрэмдэх мөнгө алга.")
        return

    success = random.random() < 0.4

    if success:
        stolen = random.randint(50, 150)
        users_data[target_id]["coins"] -= stolen
        users_data[robber_id]["coins"] += stolen
        await ctx.send(f"🥷 Амжилттай! **{ctx.author.name}**, **{member.name}**-с **${stolen}** коин дээрэмдлээ!")
    else:
        fine = 200
        users_data[robber_id]["coins"] -= fine
        mayor_data["treasury"] += fine
        await ctx.send(f"🚨 Цагдаад баригдлаа! **${fine}** торгууль төлж Хотын даргын санд орлоо.")

# ------------------ ДЭЛГҮҮР & ГЭРЛЭЛТ ------------------

@bot.command(name="shop")
async def shop(ctx):
    embed = discord.Embed(title="🛒 VIVACLOUD ДЭЛГҮҮР", color=discord.Color.purple())
    embed.add_field(name="💍 Гэрлэлтийн Бөгж", value="Үнэ: **$1,000** | Команд: `!buy ring`", inline=False)
    embed.add_field(name="🛡️ Хулгайн Хамгаалалт", value="Үнэ: **$500** | Команд: `!buy protection`", inline=False)
    embed.add_field(name="👑 VIP Роль", value="Үнэ: **$2,000** | Команд: `!buy vip`", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="buy")
async def buy(ctx, item: str):
    user_id = str(ctx.author.id)
    if user_id not in users_data:
        users_data[user_id] = {"coins": 100, "level": 1, "exp": 0, "energy": 100, "inventory": [], "protection": False, "last_daily": 0}

    item = item.lower()
    if item == "ring":
        price = 1000
    elif item == "protection":
        price = 500
    elif item == "vip":
        price = 2000
    else:
        await ctx.send("❌ Тийм бараа байхгүй байна.")
        return

    if users_data[user_id]["coins"] < price:
        await ctx.send(f"❌ Танд мөнгө хүрэлцэхгүй байна! (${price} хэрэгтэй)")
        return

    users_data[user_id]["coins"] -= price

    if item == "protection":
        users_data[user_id]["protection"] = True
        await ctx.send("🛡️ Хамгаалалт идэвхжлээ! Одоо таныг хэн ч дээрэмдэж чадахгүй.")
    elif item == "ring":
        users_data[user_id]["inventory"].append("Гэрлэлтийн Бөгж 💍")
        await ctx.send("💍 Гэрлэлтийн бөгж авлаа! (`!marry @гишүүн` гэж хүсэлт тавиарай)")
    elif item == "vip":
        role = discord.utils.get(ctx.guild.roles, name="VIP")
        if role:
            await ctx.author.add_roles(role)
            await ctx.send("🎉 VIP роль авлаа!")
        else:
            await ctx.send("✅ Авлаа (Серверт VIP роль үүсгээгүй байна).")

@bot.command(name="marry")
async def marry(ctx, member: discord.Member):
    user_id = str(ctx.author.id)
    if "Гэрлэлтийн Бөгж 💍" not in users_data.get(user_id, {}).get("inventory", []):
        await ctx.send("❌ Танд гэрлэлтийн бөгж байхгүй байна! `!shop`-оос бөгж авна уу.")
        return

    await ctx.send(f"💖 **{ctx.author.name}** гишүүн **{member.name}** руу гэрлэх хүсэлт явууллаа!")

# --- БОТЫГ АСУУХ TOKEN-ООР АЖИЛЛУУЛАХ ---
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    bot.run(TOKEN)