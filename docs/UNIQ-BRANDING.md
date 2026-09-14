# UNIQ identity — first implementation

## Compatibility
Based on upstream tag `v4.3.1.4` (`a488a4c138971c0264bf7fdc879871f68eead1e4`). Server, database, configuration and packaging sources match that tag. Java compilation targets 17; the build uses JDK 21 to match the server runtime. The compatibility branch `bftech/uniq-4.3.1.4` is based directly on that tag, with only UI and documentation changes. Remote `develop` retains its previous 4.4.0-SNAPSHOT base; do not deploy it to a 4.3.1.4 server.

## Repository map
- `ui-ngx`: Angular 20 application; Material themes, authentication, administration, dashboards and widgets.
- `application`: Java server assembly, controllers and application resources.
- `common`: shared data models, transport contracts, queues, caches and utilities.
- `dao`: persistence and database access.
- `rule-engine`: rules and processing components.
- `transport` / `netty-mqtt`: device protocol entry points.
- `edqs`: entity-data querying.
- `msa` / `docker` / `packaging`: service packaging and deployment.
- `rest-client`, `monitoring`, `tools`: clients, monitoring and development utilities.

This is an architecture and branding-path review, not a line-by-line audit of every source file.

## Brand source
The supplied UNIQ PDF specifies white #FFFFFF, light blue #7DA6FF and primary blue #0A57FC. Darker blues are derived UI shades. #071633 is a supporting dark logo background inspired by the reference, not an additional specified brand swatch.
The supplied transparent PNG is embedded unchanged in the SVG assets. Logo components use a dark background to preserve the original white lettering and blue Q; the favicon uses the Q portion of that artwork. The 4.3.1.4 layout uses the full logo in navigation.

## Implemented
- Product titles in both build environments and the initial HTML.
- Shared logo assets, dashboard logo and SVG favicon.
- Material primary/accent palettes, loading indicator and old primary-color UI defaults.
- Login logo destination, logo proportions, dashboard attribution and English sharing text across locale files.
- Original copyright attribution retained.

## Typography and scope
The user confirmed that existing typography (Roboto and the current fallbacks) should remain unchanged for this phase. Font replacement is not a pending branding task, and no additional font files are required.
Technical ThingsBoard identifiers, packages, API contracts, upstream documentation, commercial edition references and legal notices remain accurate. Email templates and mobile application branding need a separate pass.

## Verification
Source checks cover theme colors, logo XML/data references, environment titles and changed locale JSON validity (Romanian has a pre-existing syntax error at line 1403, confirmed against HEAD). A full Angular build requires project dependencies, which were absent in this checkout at review time. Browser verification remains required after dependencies and a running backend are available.
