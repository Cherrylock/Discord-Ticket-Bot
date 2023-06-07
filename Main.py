import discord
from discord.ext import commands
import sqlite3
import asyncio

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

TOKEN = 'Put bot token here'

bot = commands.Bot(command_prefix='ticket.', intents=intents)

conn = sqlite3.connect('tickets.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS tickets (
                channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER,
                author_id INTEGER
            )''')
conn.commit()

@bot.command()
async def panel(ctx, *, message=''):
    embed = discord.Embed(title='Ticket System', description=message)
    panel_message = await ctx.send(embed=embed)
    await panel_message.add_reaction('🎫')

    @bot.event
    async def on_raw_reaction_add(payload):
        if payload.message_id == panel_message.id and str(payload.emoji) == '🎫':
            guild = bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)

            await panel_message.remove_reaction('🎫', member)
            
            # Check if the user already has a ticket channel open
            c.execute("SELECT channel_id FROM tickets WHERE guild_id=? AND author_id=?", (guild.id, member.id))
            result = c.fetchone()
            
            if result is not None:
                channel_id = result[0]
                channel = guild.get_channel(channel_id)
                await member.send(f"You already have a ticket channel open <#{channel_id}>")
                return
            
            guild = ctx.guild
            category = discord.utils.get(guild.categories, name='Tickets')
            
            # Create a new ticket channel
            channel = await guild.create_text_channel(name=f'ticket-{member.id}', category=category)
            
            # Add the user to the channel
            await channel.set_permissions(member, read_messages=True, send_messages=True)
            
            # Store the ticket in the database
            c.execute("INSERT INTO tickets (channel_id, guild_id, author_id) VALUES (?, ?, ?)", (channel.id, guild.id, member.id))
            conn.commit()
            
            # Send the initial message with buttons
            embed = discord.Embed(title='Ticket System', description='Please click the button below to close the ticket.')
            ticket_message = await channel.send(embed=embed)
            await ticket_message.add_reaction('🔒')
            
            # Wait for reaction
            while True:
                try:
                    reaction_payload = await bot.wait_for("raw_reaction_add", timeout=160)
                except asyncio.TimeoutError:
                    await ticket_message.edit(content="Ticket closed due to inactivity.")
                    break
            
                if reaction_payload.channel_id == channel.id and str(reaction_payload.emoji) == '🔒':
                    await channel.send(f'{member.mention} closed the ticket.')
                    
                    # Remove the ticket from the database
                    c.execute("DELETE FROM tickets WHERE channel_id=?", (channel.id,))
                    conn.commit()
                    
                    await channel.delete()
                    break

bot.run(TOKEN)
