# PartSelect Style Guide

This style guide distills the core design language of PartSelect: a **teal‑dominant palette**, clear typography with **Roboto**, square‑edged buttons and cards, and clean layouts with plenty of breathing room. By following these guidelines you can build tools and components that feel native to PartSelect’s website.
## Brand & Design Theme

PartSelect’s interface blends utilitarian clarity with friendly accents. The site uses a **teal and gold palette** for primary and accent colors, paired with clean typography and plenty of white space. Interactive elements are clearly distinguished by color, and buttons are rectangular with no rounded corners. Icons are line‑based and usually teal or gold. The overall look is straightforward and trustworthy, reflecting the brand’s focus on genuine OEM parts and DIY repair help.

## Color Palette

![Color palette](%7B%7Bfile:file-6yGFj7c31UcmCNqQWnmtky%7D%7D)

|Color & purpose|Hex code|Usage|
|---|---|---|
|**Teal (primary)**|`#337778`|Main brand color used for links, navigation bar, icons and teal‑style buttons. Primary call‑to‑action backgrounds use teal with white text. Also appears in outlines of cards and search boxes.|
|**Gold/Yellow (accent)**|`#F3C04C`|Accent color for highlighting important actions and promotional sections. Used for orange buttons with dark text and hero backgrounds in the Water Filter Finder section. Star ratings and some icons also use this color.|
|**Black (text)**|`#121212`|Default text color and used for dark buttons (with white text). Also appears in headings and icons.|
|**White**|`#FFFFFF`|Background for most sections and buttons. White text is used on dark teal or black backgrounds.|
|**Light gray**|`#F2F2F2`|Light background panels such as the repair video section and secondary containers. Helps separate content without heavy borders.|
|**Dark gray**|`#444444`|Placeholder text color in forms and secondary body text.|
|**Medium gray**|`#777777`|Disabled text and icons; used sparingly for subtle elements.|
|**Success green**|`#41CD75` (with darker shade `#5CB332`)|Used in animation fill and success states.|
|**Error red**|`#E65532`|Error and warning messages.|

### Color usage guidelines

- **Primary color** – Use teal on interactive elements such as links, navigation backgrounds, icons and teal buttons. Text on teal should be white for sufficient contrast. Hover and active states can be created by slightly darkening the teal (e.g., reduce brightness by 15 %).
    
- **Accent color** – Use the gold/yellow tone for attention‑grabbing elements such as promotional banners, call‑to‑action buttons, badges and star ratings. Pair it with dark text for readability.
    
- **Neutral colors** – Use black for primary text and white/light gray backgrounds for content sections. Dark and medium grays are reserved for secondary text, disabled states or subtle boundaries.
    
- **Status colors** – Green signals success or positive actions (e.g., confirmation messages), while red indicates errors or warnings. Use these sparingly so they stand out.
    

## Typography

The site uses **Roboto** as its primary typeface. The CSS defines several weights of `Roboto` (Regular 400, Semi‑Bold 600 and Bold 700). A custom `EGPRoboto` font family wraps these Roboto files but falls back to standard Roboto if unavailable. There are no serifs; all text is sans‑serif and modern.

|Element|Font family & weight|Size & style|
|---|---|---|
|**Body text**|Roboto Regular (`font-weight: 400`)|16 px font size with 24 px line height (1.5×). Dark color for high contrast.|
|**Section headings**|Roboto Bold (`font-weight: 700`)|Typically 20–26 px. Main title on the home page uses 26 px and 700 weight; subheadings use 20 px.|
|**Buttons**|Roboto Semi‑Bold (`font-weight: 600`)|Medium buttons have 14–16 px font, uppercase letters and extra letter spacing. Large buttons are 18 px with 50 px height.|
|**Small text & labels**|Roboto Regular or Semi‑Bold 13–14 px|Use for captions, secondary links and footnotes. Placeholder text uses dark gray color (#444).|

### Typography guidelines

- **Consistency** – Use Roboto throughout. Reserve bold weights for headings and important metrics. Semi‑Bold (600) is appropriate for buttons and navigation labels.
    
- **Uppercase for buttons** – All button labels are uppercase to emphasize actions. Avoid using small caps or mixing case within a button.
    
- **Line spacing** – Keep body text comfortable with a 1.5× line height. Headings have slightly tighter line heights (e.g., 30 px for a 26 px heading).
    
- **Text color** – Default to dark black (#121212) for body and headings. Links and interactive text use the primary teal (#337778) and are underlined on hover.
    

## Buttons

PartSelect uses four primary button styles:

1. **Teal button** – Background teal (#337778) with white text. Medium size is 35 px tall; large size is 50 px tall. No border radius; corners are square. On hover/focus/active, the button darkens slightly (15 % brightness reduction).
    
2. **Gold button** – Background gold (#F3C04C) with black text. Used for prominent calls to action such as “Find My Filter” and newsletter sign‑ups. Hover state darkens the gold.
    
3. **Black button** – Background black (#121212) with white text. Typically used on yellow panels where contrast is needed (e.g., Water Filter Finder hero). Hover state darkens slightly.
    
4. **Ghost button** – Transparent background with a 2 px solid black border (#121212); text in black. When focused, a 3 px gold outline appears. Use for secondary actions.
    

All buttons are rectangular without rounded corners. Horizontal padding is roughly 10–25 px depending on button size. Disabled buttons appear medium gray with a light border and no pointer cursor.

## Forms & Inputs

- **Input fields** – White background with a 1 px teal border (#337778). Square corners with no border radius. Inside padding is 8 px top/bottom and 7 px left/right. Placeholder text uses dark gray (#444). On focus, outlines are removed to rely on the border color for indication.
    
- **Search boxes** – Same style as inputs but often include a teal search button attached. The search icon uses teal stroke, and the button is teal with white icon and border.
    
- **Checkboxes** – Small squares (18 px) with 2 px teal border. When checked, the background fills teal and a white checkmark appears.
    
- **Radio buttons** – Not visible on the home page but should follow similar teal border and fill conventions.
    

## Cards & Containers

- **Card borders** – Many sections display content inside cards with a 1 px teal border. Cards have square corners and white backgrounds. Use generous padding inside cards (20–30 px) and leave at least 20 px margin between cards.
    
- **Hero banners** – Promotional sections use full‑width colored panels. For example, the Water Filter Finder banner uses a gold background with dark text and an adjacent image. Keep text left‑aligned and provide ample padding.
    
- **Light panels** – Some content blocks use a light gray background (#F2F2F2) to separate them from white sections.
    

## Iconography & Imagery

- **Icons** – Use simple line‑style icons with consistent stroke width. Primary icons use teal fill (#337778); rating stars and some badges use gold fill (#F3C04C). Social media icons adopt their platform colors but are placed inside teal or neutral circles for consistency.
    
- **Illustrations** – Illustrations are minimal and clean. Product category icons are teal outlines with simple shapes (e.g., dishwasher, dryer) accompanied by teal labels. Numbers or bullet points for “Model Number Locator” use teal circles with white text.
    
- **Photography** – When using photos (e.g., hero images or customer service pictures), choose warm, realistic images that evoke home repair contexts. Images often sit next to colored text panels; maintain aspect ratios and crop to align important content.
    
- **Badges and ratings** – Use gold stars (#F3C04C) and trust badges (e.g., Trustpilot, Sitejabber) with their own brand colors. Place badges on white backgrounds with generous white space.
    

## Layout & Spacing

- **Grid** – The site relies on a responsive 12‑column grid with a maximum container width of 1200 px. Side padding is 15 px. Use equal gutters between columns. On smaller screens, cards and columns stack vertically.
    
- **Whitespace** – Generous vertical spacing (~30 px) separates sections. Inside cards and banners, maintain at least 20 px padding on all sides. Avoid crowding text next to borders.
    
- **Alignment** – Align text left for readability. Center align only short labels or icons. Navigation links are evenly spaced across the teal header.
    
- **Responsiveness** – At breakpoints (450 px, 610 px, 768 px, 910 px, etc.), adjust font sizes and container widths to ensure readability and maintain the 12‑column grid.
    

## Footer

The footer contains multiple columns of links with clear headings. Use black headings and teal links. The newsletter sign‑up panel sits above the footer with a teal background and gold call‑to‑action button. Social media icons are placed in colored circles for visual hierarchy. At the bottom is a disclaimer with small dark gray text.

## Accessibility Considerations

- Ensure sufficient color contrast for text against colored backgrounds (e.g., white text on teal and black text on gold). The chosen palette meets WCAG AA contrast ratios. Avoid placing teal text on gold backgrounds or vice versa.
    
- Provide keyboard focus styles (e.g., gold outline on ghost buttons).
    
- Use semantic HTML and ARIA labels for forms and interactive elements.
    
