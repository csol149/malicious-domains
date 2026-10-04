# Malicious Domain Blocklist

A curated list of domains observed in malicious activity, published in Adblock-style syntax for use in content blockers and DNS filtering tools.

## Categories

| Section | Meaning |
|---|---|
| Click-Fix | Domains associated with ClickFix-style social engineering, where a fake verification or error page prompts the user to run a command. |
| Unknown payload | Domains observed delivering payloads whose type has not been identified. |

## Format

```
! Title: Malicious Domain Blocklist
! Version: YYYY-MM-DD

! Click-Fix domains

||example.com^
```

- One domain per line as `||domain^`, lowercase, no paths or URLs.
- Entries are sorted alphabetically within each section.
- A domain appears once. If it fits both categories it is listed under Click-Fix.
- `Version` is the date of the last change. See [CHANGELOG.md](CHANGELOG.md) for details.

## Usage

Subscribe to the raw file in any tool that supports Adblock-style filter lists, such as uBlock Origin or AdGuard:

```
https://raw.githubusercontent.com/csol149/malicious-domains/main/domains.txt
```

## Notes on coverage

Some entries may be shared or otherwise legitimate infrastructure that was seen in attack chains. Blocking them can affect legitimate use. If a listing breaks something for you, open a false positive report.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
