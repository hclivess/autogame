# openfield demo, optional delegate: league(:delegate)
# operation demo: autogame
# operation demo: autogame:add


import json
import os
import sys
from hashlib import blake2b

import classes

config = classes.Config()
sys.path.append(config.path["modules"])

db = classes.Db(config.path["ledger"])
scores_db = classes.ScoreDb()


def go(match, iterator, coordinator, league_requirement=0):
    game = classes.Game()

    def game_saved():
        try:
            scores_db.c.execute("SELECT * FROM scores WHERE hash = ? AND saved = ? ", (game.hash, 1,))
            result = scores_db.c.fetchone()[0]
            return True
        except:
            return False

    def game_finished():
        try:
            scores_db.c.execute("SELECT * FROM scores WHERE hash = ? AND finished = ? ", (game.hash, 1,))
            result = scores_db.c.fetchone()[0]
            return True
        except:
            return False

    def db_output():

        try:
            output_weapon = hero.weapon.name
        except:
            output_weapon = None
        try:
            output_armor = hero.armor.name
        except:
            output_armor = None
        try:
            output_ring = hero.ring.name
        except:
            output_ring = None

        if not game_finished():
            scores_db.c.execute("DELETE FROM scores WHERE hash = ?", (game.hash,))
            scores_db.c.execute("INSERT INTO scores VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                game.properties["block"],
                game.hash,
                game.seed,
                hero.experience,
                json.dumps({"weapon": output_weapon, "armor": output_armor, "ring": output_ring}),
                game.league,
                game.bet,
                json.dumps(hero.damage_table),
                json.dumps(hero.defense_table),
                game.current_block,
                game.finished,
                game.saved,
                game.recipient))
            scores_db.conn.commit()

    def output(entry):
        game.step += 1
        print(entry)
        game.story[game.step] = entry

    def replay_save():
        if not os.path.exists("static"):
            os.mkdir("static")
        if not os.path.exists("static/replays"):
            os.mkdir("static/replays")

        if not game_saved() or not game_finished():
            with open(game.filename, "w") as file:
                file.write(json.dumps(game.story))
                scores_db.c.execute("UPDATE scores SET saved = 1 WHERE hash = ?", (game.hash,))
                scores_db.conn.commit()
                game.saved = True

        if not hero.alive:
            game.finished = True
            scores_db.c.execute("UPDATE scores SET finished = 1 WHERE hash = ?", (game.hash,))
            scores_db.conn.commit()

    try:
        assert ":" in match[11]
        recipient = match[11].split(":")[1]
        league = match[11].split(":")[0]
    except:
        recipient = match[2]
        league = match[11]

    game.properties = {"seed": blake2b(recipient.encode(), digest_size=24).hexdigest(),
                       "block": match[0],
                       "recipient": match[3],
                       "amount": match[4],
                       "league": league}

    game.start_block = game.properties["block"]
    game.recipient = game.properties["recipient"]
    game.bet = game.properties["amount"]
    game.current_block = game.start_block
    game.seed = game.properties["seed"]
    game.hash = blake2b((game.properties["seed"] + str(game.properties["block"])).encode(), digest_size=10).hexdigest()
    game.enemies = game.enemies

    if game.recipient == coordinator and game.bet >= league_requirement:
        game.league = game.properties["league"]
    else:
        game.league = "casual"

    game.filename = "static/replays/" + str(game.hash + ".json")

    hero = classes.Hero()

    if game_finished():
        game.quit = True
        print(f"Game {game.hash} tagged as finished, skipping")

    # trigger is followed by events affected by modifiers

    # define events

    EVENTS = {game.properties["seed"][2:4]: "attack",
              game.properties["seed"][4:6]: "attacked",
              game.properties["seed"][6:8]: "attack_critical"}

    # define triggers

    def enemy_dead_check():
        if enemy.health < 1:
            hero.in_combat = False
            enemy.alive = False
            output(f"{enemy.name} died")
            output(f"You now have {hero.experience} experience")

    def hero_dead_check():
        if hero.health < 1:
            hero.alive = False
            output(f"You died with {hero.experience} experience")

    def chaos_ring():
        if not hero.ring:
            output(f'You see a chaos ring, the engraving says {subcycle["cycle_hash"][0:5]}')
            if subcycle["cycle_hash"][0] in ["0", "1", "2", "3", "4"]:
                hero.ring = classes.ChaosRing().roll_good()
            else:
                hero.ring = classes.ChaosRing().roll_bad()

            hero.full_hp += hero.ring.health_modifier

            if hero.health > hero.full_hp:
                hero.health = hero.full_hp

            output(hero.ring.string)

    def ragnarok():
        output(f"Ragnarök begins")
        # add new monsters to the world
        for enemy in classes.Game().enemies_ragnarok:
            game.enemies.append(enemy)

    def attack():
        hero.experience += 1
        damage = hero.damage
        enemy.health -= hero.damage
        output(f"{enemy.name} suffers {damage} damage and is left with {enemy.health} HP")
        enemy_dead_check()

    def attack_critical():
        hero.experience += 1
        damage = hero.damage + hero.experience
        enemy.health -= damage
        output(f"{enemy.name} suffers {damage} *critical* damage and is left with {enemy.health} HP")
        enemy_dead_check()

    def cycle():
        db.c.execute("SELECT * FROM transactions WHERE block_height = ? ORDER BY block_height", (game.current_block,))
        result = db.c.fetchall()

        position = 0
        game.cycle = {}  # remove previous cycle if exists
        for tx in result:
            position = position + 1

            block_height = tx[0]
            timestamp = tx[1]
            address = tx[2]
            recipient = tx[3]
            amount = tx[4]
            block_hash = tx[7]
            operation = tx[10]
            data = tx[11]

            cycle_hash = blake2b((str(tx)).encode(), digest_size=60).hexdigest()

            game.cycle[position] = {"block_height": block_height, "timestamp": timestamp, "address": address,
                                    "recipient": recipient, ":amount": amount, "block_hash": block_hash,
                                    "operation": operation, "data": data, "cycle_hash": cycle_hash}

    def attacked():
        damage_taken = enemy.damage

        if hero.armor:
            damage_taken -= hero.defense

        hero.health = hero.health - damage_taken

        output(f"{enemy.name} hits you for {enemy.damage} HP, you now have {hero.health} HP")
        hero_dead_check()

    while hero.alive and not game.quit:

        cycle()
        if not game.cycle:
            output("The game is still running")
            game.quit = True
            break

        for subposition, subcycle in game.cycle.items():  # for tx in block
            # print (subcycle)

            # human interaction
            for item_interactive_class in classes.items_interactive:
                if item_interactive_class().trigger == subcycle["data"] and subcycle["address"] == game.seed and \
                        subcycle["operation"] == game.interaction_string:
                    if item_interactive_class == classes.ChaosRing:
                        chaos_ring()

            for events_interactive_global_class in classes.events_interactive_global:
                if events_interactive_global_class().trigger == subcycle["data"] and subcycle[
                    "operation"] == game.interaction_string:
                    if events_interactive_global_class == classes.Ragnarok:
                        ragnarok()
            # human interaction

            if iterator == 2:
                for pvp_class in game.pvp:
                    if pvp_class().trigger == subcycle["data"] and subcycle["operation"] == game.interaction_string and \
                            subcycle["recipient"] == game.seed and hero.pvp_interactions > 0:
                        attacker = subcycle["address"]
                        try:
                            scores_db.c.execute(
                                "SELECT damage FROM scores WHERE seed = ? AND block_start <= ? AND block_end >= ? ORDER BY block_start DESC LIMIT 1",
                                (attacker, game.current_block, game.current_block,))

                            enemy_damage_table = json.loads(scores_db.c.fetchone()[0])

                            for enemy_damage_block, enemy_damage_value in enemy_damage_table.items():
                                if int(enemy_damage_block) <= game.current_block:
                                    enemy_damage = int(enemy_damage_value)

                            hero.health = hero.health - (enemy_damage - hero.defense)
                            hero.pvp_interactions -= 1
                            hero_dead_check()

                            output(
                                f"Player {attacker} hits you and you lose {enemy_damage - hero.defense} health down to {hero.health}")

                        except Exception:
                            output(f"Player {attacker} tried to attack you, but they failed")

            for potion_class in game.potions:
                if potion_class().trigger in subcycle["cycle_hash"] and not hero.in_combat:

                    if potion_class == classes.HealthPotion and hero.health < hero.full_hp:

                        if hero.in_combat:
                            hero.health = hero.health + classes.HealthPotion().heal_in_combat
                            output(f"You drink a potion and heal to {hero.health} HP...")

                        elif not hero.in_combat:
                            hero.health = hero.health + classes.HealthPotion().heal_not_in_combat
                            output(f"You rest and heal well to {hero.health} HP...")

                        if hero.health > hero.full_hp:
                            hero.health = hero.full_hp

            for armor_class in game.armors:
                if armor_class().trigger in subcycle["cycle_hash"] and not hero.in_combat:
                    if not hero.armor:
                        hero.armor = armor_class()
                        hero.defense += hero.armor.defense
                        hero.defense_table[game.current_block] = hero.defense

                        output(f"You obtained {armor_class().name}")

            for weapon_class in game.weapons:
                if weapon_class().trigger in subcycle["cycle_hash"] and not hero.in_combat:
                    if not hero.weapon:
                        hero.weapon = weapon_class()
                        hero.damage += hero.weapon.damage
                        hero.damage_table[game.current_block] = hero.damage

                        output(f"You obtained {weapon_class().name}")

            for enemy_class in game.enemies:
                if enemy_class().trigger in subcycle["cycle_hash"] and hero.alive and not hero.in_combat:
                    enemy = enemy_class()

                    output(f"You meet {enemy.name} on transaction {subposition} of block {game.current_block}")
                    hero.in_combat = True

            for event_key in EVENTS:  # check what happened
                if hero.in_combat and hero.alive and not game.quit:

                    if event_key in subcycle["cycle_hash"] and enemy.alive:
                        event = EVENTS[event_key]
                        output(f"Event: {event}")

                        if event == "attack":
                            attack()

                        elif event == "attack_critical":
                            attack_critical()

                        elif event == "attacked":
                            attacked()

        game.current_block = game.current_block + 1

    if iterator == 2:  # db iteration finished, now save the story (player interactions serial, based on db)
        replay_save()

    db_output()

    return game, hero
