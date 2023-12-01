
# Pibald Recolors

This is a Blender plugin that supports the work-in-progress renderer "Pibald." It adds a panel and custom properties for making mutiple vertex color palettes on a single model.

Despite it being designed for use a work-in-progress rendering program, it could also find use with anyone looking to add color palettes to their game assets and can handle writing their own script for exporting the color data.
## Usage

- Before setting up your basis colors, ensure that your mesh has at least one entry in the color attributes section of its data tab, and that the attribute is of the format "Face Corner > Byte Color."
- Apply a unique color for every desired entry in the palette, or simply color the model according to its default appearance as a starting point.
- Press the plus button in the recolor panel to add the basis palette, then the refresh button to populate it with the current vertex volors. At this point I would also recommend labelling each entry in the palette. Depending on your viewport's gamma correction, it can be hard to find a particular color on a model if you're looking at it in the panel.
- Press the plus button to add a new color palette. Click the radio button next to it to switch to it.
- Click on the colors in any palette to open up a color picker that will set their value.
- Press the minus button to remove a color palette you no longer wish to keep. This cannot be used on the basis palette once it's been added.
- Add and remove palette colors by editing the vertex colors of the model while the basis palette is selected, then hitting the refresh button to reflect your changes in the basis palette. New palette entries will start with their basis color in all other palettes.
## Screenshots

Example basis palette for a character model:
![basis](/screenshots/basis_palette.png)

A palette for use in game: 
![rhodope](/screenshots/default.png)

Another palette that could be used to reference a really cool goat character or something: 
![absa](/screenshots/hire_me_daniel.png)


## Issues

- Undoing color changes had to be done by tracking the time elapsed between changes for blender api reasons. You might undo more than you'd like if you're taking less than a second or two between changing colors.