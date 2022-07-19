# arksan
Arknights material sanity value (MSV) calculator + data analysis of upgrade costs

## About
The methodology for calculating MSVs is based on [Moe's material farming spreadsheet](https://docs.google.com/spreadsheets/d/12X0uBQaN7MuuMWWDTiUjIni_MOP015GnulggmBJgBaQ/edit#gid=1960303262).
Skill mastery costs for all 6* operators are calculated based on MSVs when each operator debuted.
Non-permanent event stages are not included in the calculations.

## How to use
Run graph.py to get started. The program will save graphs of operators' skill mastery costs to the project folder.

## Graphs
![mastery_costs_bar](https://user-images.githubusercontent.com/88992929/179646621-617275ce-eddd-4388-bf86-af71ef4df518.png)
![mastery_costs_hist](https://user-images.githubusercontent.com/88992929/179647101-1e18901d-2c2c-4d44-a030-01a8cff0033a.png)

## Dependencies
- dateparser `v1.1.1`
- lxml `v4.9.1`
- matplotlib `v3.5.2`
- numpy `v1.22.4`
- pandas `v1.4.3`
- requests `v2.28.1`
- seaborn `v0.11.2`
