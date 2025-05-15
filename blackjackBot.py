import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import random
import datetime
import pytz

class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_data = {}
        self.yesterday_top_user = None
        self.cards = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.card_values = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
            '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11
        }
        self.daily_reset.start()

    def deal_card(self):
        return random.choice(self.cards)

    def calculate_score(self, hand):
        score = sum(self.card_values[card] for card in hand)
        ace_count = hand.count('A')
        while score > 21 and ace_count:
            score -= 10
            ace_count -= 1
        return score

    @tasks.loop(minutes=1)
    async def daily_reset(self):
        now = datetime.datetime.now(pytz.timezone('Europe/Tallinn'))
        if now.hour == 0 and now.minute == 0:
            top_user_id = max(self.user_data.items(), key=lambda x: x[1]['coins'])[0] if self.user_data else None
            for user_id, data in self.user_data.items():
                data["last_claim"] = None
                data["claimed_winner"] = False
            if top_user_id:
                self.yesterday_top_user = top_user_id
                print(f"Daily reset complete. Top user: {top_user_id}")

    @commands.command()
    async def claim(self, ctx):
        user = ctx.author
        now = datetime.datetime.utcnow()
        data = self.user_data.get(user.id, {"coins": 0, "last_claim": None, "claimed_winner": False})

        if data["last_claim"] and data["last_claim"].date() == now.date():
            await ctx.send(f"{user.mention}, you have already claimed your daily reward today.")
            return

        data["coins"] += 50
        data["last_claim"] = now
        self.user_data[user.id] = data
        await ctx.send(f"{user.mention}, you claimed 50 coins! You now have {data['coins']} coins.")

    @commands.command()
    async def winnerclaim(self, ctx):
        if ctx.author.id != self.yesterday_top_user:
            await ctx.send("You're not yesterday's top user.")
            return
        data = self.user_data.get(ctx.author.id, {"coins": 0, "claimed_winner": False})
        if data.get("claimed_winner", False):
            await ctx.send("You've already claimed your winner reward today.")
            return
        data["coins"] += 100
        data["claimed_winner"] = True
        self.user_data[ctx.author.id] = data
        await ctx.send(f"{ctx.author.mention}, you claimed your 100-coin winner reward!")

    @commands.command()
    async def balance(self, ctx):
        user = ctx.author
        coins = self.user_data.get(user.id, {"coins": 0})["coins"]
        await ctx.send(f"{user.mention}, you have {coins} coins.")

    @commands.command()
    async def leaderboard(self, ctx):
        sorted_users = sorted(self.user_data.items(), key=lambda x: x[1]["coins"], reverse=True)
        embed = discord.Embed(title="Leaderboard", color=discord.Color.gold())
        for idx, (uid, data) in enumerate(sorted_users[:10]):
            user = self.bot.get_user(uid)
            embed.add_field(name=f"{idx + 1}. {user}", value=f"{data['coins']} coins", inline=False)
        await ctx.send(embed=embed)

    # Your existing Blackjack game code including View, hit/stand/double logic, etc., goes here
    # For brevity, I’ll stop the injection here, but I can fully integrate the split hand logic next.

    # Placeholder for Blackjack game logic...
    class BlackjackView(View):
        def __init__(self, cog, player, hand, dealer_hand, bet):
            super().__init__(timeout=120)
            self.cog = cog
            self.player = player
            self.hand = hand
            self.dealer_hand = dealer_hand
            self.bet = bet
            self.has_hit = False
            self.message = None

        async def update_embed(self, interaction):
            score = self.cog.calculate_score(self.hand)
            dealer_visible = self.dealer_hand[0] + ' ❓'
            embed = discord.Embed(
                title=f"{self.player.display_name}'s Blackjack Game",
                description=f"**Your Hand:** {' '.join(self.hand)}\n**Total:** {score}\n\n**Dealer's Hand:** {dealer_visible}\n\nChoose an action:",
                color=discord.Color.green()
            )
            for item in self.children:
                if item.label == "2x":
                    item.disabled = self.has_hit
            await interaction.response.edit_message(embed=embed, view=self)

        @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary)
        async def hit_button(self, interaction: discord.Interaction, button: Button):
            if interaction.user != self.player:
                await interaction.response.send_message("This isn't your game.", ephemeral=True)
                return

            self.hand.append(self.cog.deal_card())
            self.has_hit = True
            score = self.cog.calculate_score(self.hand)
            if score > 21:
                embed = discord.Embed(
                    title="You busted!",
                    description=f"Your Hand: {' '.join(self.hand)} (Total: {score})",
                    color=discord.Color.red()
                )
                self.stop()
                await interaction.response.edit_message(embed=embed, view=None)
            else:
                await self.update_embed(interaction)

        @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary)
        async def stand_button(self, interaction: discord.Interaction, button: Button):
            if interaction.user != self.player:
                await interaction.response.send_message("This isn't your game.", ephemeral=True)
                return

            await self.end_game(interaction)

        @discord.ui.button(label="2x", style=discord.ButtonStyle.danger)
        async def double_button(self, interaction: discord.Interaction, button: Button):
            if interaction.user != self.player:
                await interaction.response.send_message("This isn't your game.", ephemeral=True)
                return

            data = self.cog.user_data.get(self.player.id, {"coins": 0})
            if data["coins"] < self.bet:
                await interaction.response.send_message("You don't have enough coins to double down.", ephemeral=True)
                return

            self.bet *= 2
            data["coins"] -= self.bet // 2
            self.cog.user_data[self.player.id] = data

            self.hand.append(self.cog.deal_card())
            self.clear_items()
            await self.end_game(interaction)

        async def end_game(self, interaction):
            player_score = self.cog.calculate_score(self.hand)
            dealer_score = self.cog.calculate_score(self.dealer_hand)

            while dealer_score < 17:
                self.dealer_hand.append(self.cog.deal_card())
                dealer_score = self.cog.calculate_score(self.dealer_hand)

            result = f"**Your Hand:** {' '.join(self.hand)} (Total: {player_score})\n"
            result += f"**Dealer's Hand:** {' '.join(self.dealer_hand)} (Total: {dealer_score})\n"

            data = self.cog.user_data.get(self.player.id, {"coins": 0})

            if player_score > 21:
                result += "\n**Bust!** You lost your bet."
            elif dealer_score > 21 or player_score > dealer_score:
                win_amount = int(self.bet * 2.5) if player_score == 21 and len(self.hand) == 2 else self.bet * 2
                result += f"\n**You win!** You earned {win_amount} coins!"
                data["coins"] += win_amount
            elif player_score < dealer_score:
                result += "\n**Dealer wins!** You lost your bet."
            else:
                result += "\n**It's a tie!** You get your bet back."
                data["coins"] += self.bet

            self.cog.user_data[self.player.id] = data
            self.stop()

            embed = discord.Embed(title="Game Over", description=result, color=discord.Color.blue())
            await interaction.response.edit_message(embed=embed, view=None)

    @commands.command()
    async def blackjack(self, ctx, bet: int):
        player = ctx.author
        data = self.user_data.get(player.id, {"coins": 0, "last_claim": None})

        if bet <= 0:
            await ctx.send(f"{player.mention}, your bet must be greater than 0.")
            return

        if data["coins"] < bet:
            await ctx.send(f"{player.mention}, you don't have enough coins to bet {bet}.")
            return

        hand = [self.deal_card(), self.deal_card()]
        dealer_hand = [self.deal_card(), self.deal_card()]
        player_score = self.calculate_score(hand)
        dealer_score = self.calculate_score(dealer_hand)

        if dealer_score == 21 and (
                '10' in dealer_hand or 'J' in dealer_hand or 'Q' in dealer_hand or 'K' in dealer_hand or 'A' in dealer_hand):
            dealer_str = ' '.join(dealer_hand)
            embed = discord.Embed(title="Dealer has Blackjack!",
                                  description=f"Dealer's Hand: {dealer_str}\nYou lost your bet.",
                                  color=discord.Color.red())
            data["coins"] -= bet
            self.user_data[player.id] = data
            await ctx.send(embed=embed)
            return

        data["coins"] -= bet
        self.user_data[player.id] = data

        view = self.BlackjackView(self, player, hand, dealer_hand, bet)
        embed = discord.Embed(
            title=f"{player.display_name}'s Blackjack Game",
            description=f"**Your Hand:** {' '.join(hand)}\n**Total:** {player_score}\n\n**Dealer's Hand:** {dealer_hand[0]} ❓\n\nChoose an action:",
            color=discord.Color.green()
        )
        message = await ctx.send(embed=embed, view=view)
        view.message = message

def setup(bot):
    bot.add_cog(Blackjack(bot))

"""import discord
from AppData.Local.Programs.Python.Python313.Lib.logging import disable
from discord.ext import commands
from discord.ui import Button, View
import random
import datetime

class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_data = {}
        self.cards = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.card_values = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
            '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11
        }

    def deal_card(self):
        return random.choice(self.cards)

    def calculate_score(self, hand):
        score = sum(self.card_values[card] for card in hand)
        ace_count = hand.count('A')
        while score > 21 and ace_count:
            score -= 10
            ace_count -= 1
        return score

    @commands.command()
    async def claim(self, ctx):
        user = ctx.author
        now = datetime.datetime.utcnow()
        data = self.user_data.get(user.id, {"coins": 0, "last_claim": None})
        cooldown = datetime.timedelta(hours=20)

        last_claim = data.get("last_claim")
        if last_claim and now - last_claim < cooldown:
            remaining = cooldown - (now - last_claim)
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes = remainder // 60
            await ctx.send(f"{user.mention}, you can claim again in {remaining.days * 24 + hours}h {minutes}m.")
            return

        data["coins"] += 50
        data["last_claim"] = now
        self.user_data[user.id] = data
        await ctx.send(f"{user.mention}, you claimed 50 coins! You now have {data['coins']} coins.")

    @commands.command()
    async def balance(self, ctx):
        user = ctx.author
        coins = self.user_data.get(user.id, {"coins": 0})["coins"]
        await ctx.send(f"{user.mention}, you have {coins} coins.")

    class BlackjackView(View):
        def __init__(self, cog, player, hand, dealer_hand, bet):
            super().__init__(timeout=120)
            self.cog = cog
            self.player = player
            self.hand = hand
            self.dealer_hand = dealer_hand
            self.bet = bet
            self.has_hit = False
            self.message = None

        async def update_embed(self, interaction):
            score = self.cog.calculate_score(self.hand)
            dealer_visible = self.dealer_hand[0] + ' ❓'
            embed = discord.Embed(
                title=f"{self.player.display_name}'s Blackjack Game",
                description=f"**Your Hand:** {' '.join(self.hand)}\n**Total:** {score}\n\n**Dealer's Hand:** {dealer_visible}\n\nChoose an action:",
                color=discord.Color.green()
            )
            for item in self.children:
                if item.label == "2x":
                    item.disabled = self.has_hit
            await interaction.response.edit_message(embed=embed, view=self)

        @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary)
        async def hit_button(self, interaction: discord.Interaction, button: Button):
            if interaction.user != self.player:
                await interaction.response.send_message("This isn't your game.", ephemeral=True)
                return

            self.hand.append(self.cog.deal_card())
            self.has_hit = True
            score = self.cog.calculate_score(self.hand)
            if score > 21:
                embed = discord.Embed(
                    title="You busted!",
                    description=f"Your Hand: {' '.join(self.hand)} (Total: {score})",
                    color=discord.Color.red()
                )
                self.stop()
                await interaction.response.edit_message(embed=embed, view=None)
            else:
                await self.update_embed(interaction)

        @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary)
        async def stand_button(self, interaction: discord.Interaction, button: Button):
            if interaction.user != self.player:
                await interaction.response.send_message("This isn't your game.", ephemeral=True)
                return

            await self.end_game(interaction)

        @discord.ui.button(label="2x", style=discord.ButtonStyle.danger)
        async def double_button(self, interaction: discord.Interaction, button: Button):
            if interaction.user != self.player:
                await interaction.response.send_message("This isn't your game.", ephemeral=True)
                return


            data = self.cog.user_data.get(self.player.id, {"coins": 0})
            if data["coins"] < self.bet:
                await interaction.response.send_message("You don't have enough coins to double down.", ephemeral=True)
                return

            self.bet *= 2
            data["coins"] -= self.bet // 2
            self.cog.user_data[self.player.id] = data

            self.hand.append(self.cog.deal_card())
            self.clear_items()
            await self.end_game(interaction)

        async def end_game(self, interaction):
            player_score = self.cog.calculate_score(self.hand)
            dealer_score = self.cog.calculate_score(self.dealer_hand)

            while dealer_score < 17:
                self.dealer_hand.append(self.cog.deal_card())
                dealer_score = self.cog.calculate_score(self.dealer_hand)

            result = f"**Your Hand:** {' '.join(self.hand)} (Total: {player_score})\n"
            result += f"**Dealer's Hand:** {' '.join(self.dealer_hand)} (Total: {dealer_score})\n"

            data = self.cog.user_data.get(self.player.id, {"coins": 0})

            if player_score > 21:
                result += "\n**Bust!** You lost your bet."
            elif dealer_score > 21 or player_score > dealer_score:
                win_amount = int(self.bet * 2.5) if player_score == 21 and len(self.hand) == 2 else self.bet * 2
                result += f"\n**You win!** You earned {win_amount} coins!"
                data["coins"] += win_amount
            elif player_score < dealer_score:
                result += "\n**Dealer wins!** You lost your bet."
            else:
                result += "\n**It's a tie!** You get your bet back."
                data["coins"] += self.bet

            self.cog.user_data[self.player.id] = data
            self.stop()

            embed = discord.Embed(title="Game Over", description=result, color=discord.Color.blue())
            await interaction.response.edit_message(embed=embed, view=None)

    @commands.command()
    async def blackjack(self, ctx, bet: int):
        player = ctx.author
        data = self.user_data.get(player.id, {"coins": 0, "last_claim": None})

        if bet <= 0:
            await ctx.send(f"{player.mention}, your bet must be greater than 0.")
            return

        if data["coins"] < bet:
            await ctx.send(f"{player.mention}, you don't have enough coins to bet {bet}.")
            return

        hand = [self.deal_card(), self.deal_card()]
        dealer_hand = [self.deal_card(), self.deal_card()]
        player_score = self.calculate_score(hand)
        dealer_score = self.calculate_score(dealer_hand)

        if dealer_score == 21 and ('10' in dealer_hand or 'J' in dealer_hand or 'Q' in dealer_hand or 'K' in dealer_hand or 'A' in dealer_hand):
            dealer_str = ' '.join(dealer_hand)
            embed = discord.Embed(title="Dealer has Blackjack!", description=f"Dealer's Hand: {dealer_str}\nYou lost your bet.", color=discord.Color.red())
            data["coins"] -= bet
            self.user_data[player.id] = data
            await ctx.send(embed=embed)
            return

        data["coins"] -= bet
        self.user_data[player.id] = data

        view = self.BlackjackView(self, player, hand, dealer_hand, bet)
        embed = discord.Embed(
            title=f"{player.display_name}'s Blackjack Game",
            description=f"**Your Hand:** {' '.join(hand)}\n**Total:** {player_score}\n\n**Dealer's Hand:** {dealer_hand[0]} ❓\n\nChoose an action:",
            color=discord.Color.green()
        )
        message = await ctx.send(embed=embed, view=view)
        view.message = message

def setup(bot):
    bot.add_cog(Blackjack(bot))"""