# UNIQ identity — first implementation

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
The supplied transparent PNG is embedded unchanged in the SVG assets. Light surfaces use a dark badge to preserve the original white lettering; compact navigation and favicon use the Q portion of that artwork.

## Implemented
- Product titles in both build environments and the initial HTML.
- Shared logo assets, dashboard logo, compact navigation and SVG favicon.
- Material primary/accent palettes, loading indicator and old primary-color UI defaults.
- Login logo destination, logo proportions, dashboard attribution and English sharing text across locale files.
- Original copyright attribution retained.

## Typography and scope
The user confirmed that existing typography (Roboto and the current fallbacks) should remain unchanged for this phase. Font replacement is not a pending branding task, and no additional font files are required.
Technical ThingsBoard identifiers, packages, API contracts, upstream documentation, commercial edition references and legal notices remain accurate. Email templates and mobile application branding need a separate pass.

## Verification
Source checks cover theme colors, logo XML/data references, environment titles and changed locale JSON validity (Romanian has a pre-existing syntax error at line 1403, confirmed against HEAD). A full Angular build requires project dependencies, which were absent in this checkout at review time. Browser verification remains required after dependencies and a running backend are available.
