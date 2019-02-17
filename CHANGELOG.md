# Changelog

## v0.15.1

- Show already guessed letters in hangman
- Remove responding to invalid guesses in hangman (unless entire word)

## v0.15.0

- Added hangman, as proof of concept game!

## v0.14.1

- Fixed issue when channels had emoji in their names and a DB was set up badly

## v0.14.0

- Move admin and ping commands into groups of subcategories, to clean up commands (run `help` to see new subcategories)
- Added hidden redirects for old user facing commands to ease into transition
- Added sharding support when running at scale
- Added command to get average latency of bot, and specific information about best and worst shards currently

## v0.13.2

- Made flag output prettier, with actual mentions and links

## v0.13.1

- Added "github" command to get github link

## v0.13

- Renamed "slurs" cog to "flags"
- Changed flags to work per server, instead of being global
- Fixed minor bugs
## v0.12

- Made roles per server instead of global on the bot
- Add `my_roles` command to list roles you are a part of currently
- Set roles to is_joinable when being imported if they are currently mentionable
- Cleanup of root directory

## v0.11

Start of changelog