import os
import discord
from datetime import datetime, timedelta
from stockbotmodel import Stocker
from discord.ext import commands
from configparser import ConfigParser
from newsapi import NewsApiClient
import pandas as pd
import requests
import re
import time

version = "0.0.4"

bot = commands.Bot(command_prefix="$")
bot.remove_command("help")


def get_symbol(symbol):
    url = "http://d.yimg.com/autoc.finance.yahoo.com/autoc?query={}&region=1&lang=en".format(symbol)

    result = requests.get(url).json()

    for x in result['ResultSet']['Result']:
        if x['symbol'] == symbol:
            return x['name']


def get_info(key):
    config_parser = ConfigParser()
    config_filepath = "importantinfos.txt"
    config_parser.read(config_filepath)
    if key.lower() == "newsapi":
        return config_parser['API']['newsapi']
    elif key.lower() == "token":
        return config_parser["TOKEN"]["discord_token"]
    print("Unable to find the info")



def log(message):
    log_file = open("botlog.txt", "a")
    time = datetime.now().strftime("%Y-%m-%d %H:%M")
    log_file.write(f"{time} -- {message}\n")
    log_file.close()


def cleanhtml(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext


@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.idle, activity=discord.Game("$help"))
    print(f"Stockord Bot v{version} is ready")


@bot.command()
async def help(ctx):
    embed = discord.Embed(colour=discord.Colour.blue())
    embed.set_author(name="Stockord Help")
    embed.add_field(name="Author", value="[101DollarFootLong](https://github.com/101DollarFootLong)", inline=True)
    embed.add_field(name="Verison", value=version, inline=True)
    embed.add_field(name="Gets stock graph data - $graph", value="```py\n# graph syntax\n s=stock symbol\n "
                                                        "b=began date(YYYY-MM-DD)\n "
                                                        "e=end date(YYYY-MM-DD) \n# b and e are optionals"
                                                        "\n# Ex: $graph s=aapl b=2019-08-01 e=2020-02-02```",
                    inline=False)
    embed.add_field(name="Gets stock prediction - $predict",
                    value="```py\n# $predict syntax\n s=stock symbol\n n=number of days\n "
                          "b=began date(YYYY-MM-DD)\n "
                          "c=changing point vaulue \n# b and c are optionals"
                          "\n# Ex: $predict s=aapl n=10 b=2020-01-01 c=0.5```", inline=False)
    embed.add_field(name="Gets the latest news - $news", value="$news stock_symbol", inline=False)
    # embed.set_author(name="Thien Le", icon_url="https://avatars2.githubusercontent.com/u/54750578?s=460&u"
    #                                            "=2596855a5494a5d020d1a3925eabca9ca522021c&v=4")
    log(f"{ctx.message.author} call on help")
    await ctx.send(content=None, embed=embed)


@bot.command()
# TODO: Change the format to dict
async def graph(ctx, *, message):
    continue_flag = True
    try:
        end_date = datetime.strftime(datetime.now() - timedelta(0), "%Y-%m-%d")
        dict_strings = dict([x.split("=") for x in message.lower().split()])
        stock_name = dict_strings["s"]

        if "b" in dict_strings.keys():
            start_date = dict_strings["b"]
        else:
            start_date = '2000-01-01'

        if "e" in dict_strings.keys():
            end_date = dict_strings["e"]
    except Exception:
        continue_flag = False
        await ctx.send("```py\n# graph syntax\n s=stock symbol\n "
                                                        "b=began date(YYYY-MM-DD)\n "
                                                        "e=end date(YYYY-MM-DD) \n# b and e are optionals"
                                                        "\n# Ex: $graph s=aapl b=2019-08-01 e=2020-02-02```")
    if continue_flag:
        try:
            # stock = web.DataReader(stock_name, data_source='yahoo', start='2012-01-01', end=end_date)
            stock_val_s = Stocker(stock_name, start_date, end_date)
            file_name = stock_val_s.plot_stock(save=True)
            await ctx.send(content=f"Here is the {stock_name} stock from {start_date} to {end_date}",
                           file=discord.File(file_name))
            os.remove(file_name)
            log(f"{ctx.message.author} call on {message}")

        except Exception as e:
            print(e)
            await ctx.send("Please enter a valid stock tag")


@bot.command()
async def predict(ctx, *, message):
    continue_flag = True
    try:
        # split up by space then split up by = sign and ignore the command string
        dict_strings = dict([x.split("=") for x in message.split()])
        print(dict_strings)
        stock_name = dict_strings["s"]
        num_days = int(dict_strings["n"])

        if "b" in dict_strings.keys():
            end_date = dict_strings["b"]
        else:
            end_date = datetime.strftime(datetime.now() - timedelta(0), "%Y-%m-%d")

        # Default changing point scale
        default_cps = True
        if "c" in dict_strings.keys():
            changing_point_scale = float(dict_strings["c"])
        else:
            default_cps = False
    except Exception:
        continue_flag = False
        await ctx.send("```py\n# predict syntax\n s=stock symbol\n n=number of days\n b=began date\n "
                       "c=changing point vaulue \n# b and c are optionals\n# Ex: $predict s=aapl n=10 b=2020-01-01 c=0.5```")
    if continue_flag:
        try:
            # stock = web.DataReader(stock_name, data_source='yahoo', start='2012-01-01', end=end_date)
            for stock in stock_name.split(","):
                stock_val_p = Stocker(stock, enddate=end_date)
                print(stock)

                await ctx.send("Generating the model, please wait..")
                start_time = time.time()
                model, model_data, model_path = stock_val_p.create_prophet_model(save=True)
                # await channel.send(content=f"Here is the prophet model", file=discord.File(model_path))

                m_embed = discord.Embed(title="Model Generated", color=discord.Colour.blue())
                model_embed_file = discord.File(model_path, filename="model_embeded.png")
                m_embed.set_image(url="attachment://model_embeded.png")
                await ctx.send(file=model_embed_file, embed=m_embed)

                await ctx.send("Evaluating the parameters for the model. Please wait..")
                weekly_seasonality = True
                stock_val_p.weekly_seasonality = weekly_seasonality

                if not default_cps:
                    changing_point_scale = stock_val_p.changepoint_prior_validation()

                stock_val_p.changepoint_prior_scale = changing_point_scale

                predicted_path = stock_val_p.predict_future(days=num_days, save=True)
                # await channel.send(content=f"Here is prediction {stock_name} stock for {num_days} days",
                #                    file=discord.File(predicted_path))

                total_time = round((time.time() - start_time), 2)
                # embeding the message
                p_embed = discord.Embed(title=f"{stock} Prediction for {num_days} days", color=discord.Colour.blue())

                # linking the file names

                predicted_embed_file = discord.File(predicted_path, filename="predicted_embeded.png")

                p_embed.add_field(name="Best changing point value", value=changing_point_scale, inline=True)
                p_embed.add_field(name="Weekly Seasonality", value=str(weekly_seasonality), inline=True)
                p_embed.add_field(name="Time took", value=f"{str(total_time)} seconds", inline=True)
                p_embed.set_image(url="attachment://predicted_embeded.png")
                await ctx.send(file=predicted_embed_file, embed=p_embed)

                # add Reactions to msgs
                # msg = await ctx.send(file=predicted_embed_file, embed=embed)
                # reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
                # [await msg.add_reaction(x) for x in reactions]

                os.remove(model_path)
                os.remove(predicted_path)
                log(f"{ctx.message.author} call on {message}")
        except Exception as e:
            print(e)
            await ctx.send("Invalid stock symbol / Insufficient stock data(at least one years)")


@bot.command()
async def news(ctx, *, message):
    user_message = message.upper().split()
    stock_name = user_message[0]
    company_name = get_symbol(stock_name)
    if company_name:

        print(f"Pre-clean: {company_name}")

        company_name = " ".join(re.findall(r"[\w']+", company_name))
        stop_words = ["the", "company", "holdings", "corporation", "inc"]
        fixed_name = [word for word in company_name.split() if word.lower() not in stop_words]
        company_name = " ".join(fixed_name)

        print(f"Post-clean: {company_name}")

        from_date = datetime.strftime(datetime.now() - timedelta(5), "%Y-%m-%d")
        to_date = datetime.strftime(datetime.now() - timedelta(0), "%Y-%m-%d")
        newsapi = NewsApiClient(api_key=get_info("newsapi"))
        try:
            articles = newsapi.get_everything(qintitle=company_name,
                                              from_param=from_date, domains="yahoo.com",
                                              to=to_date,
                                              language='en')

            news_df = pd.DataFrame(articles['articles'])
            news_df.sort_values("publishedAt", ascending=False, inplace=True)

            embed = discord.Embed(color=discord.Colour.blue())
            embed.set_author(name=f"The Latest News for {stock_name} stock")
            count = 0
            for index, content in news_df.iterrows():
                if not content.isnull().any() and count < 4:
                    description = cleanhtml(content.description[:200]).replace("\n", "-")
                    embed.add_field(name=f"{content.publishedAt[:15]}", value=f"Title: {content.title}\nDescription: \
                                                                    {description}..\n[Read More]({content.url})",
                                    inline=False)
                    count += 1
            await ctx.send(content=None, embed=embed)
            log(f"{ctx.message.author} call on {message}")
        except Exception as e:
            log(f"Error: {e}")
            await ctx.send("No news found.")
    else:
        await ctx.send("Please provide a valid stock symbol")


# TODO: Dividend

@bot.event
async def on_command_error(ctx, error):
    log(f"{ctx.message.author} -- {error}")
    print(f"Error -- {error}")


token = get_info("token")
bot.run(token)
