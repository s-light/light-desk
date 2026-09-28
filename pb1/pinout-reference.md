# PocketBeagle 1 (original) pin mux reference

> [!NOTE]
> Extracted from the official BeagleBoard docs P1/P2 header connector
> tables at <https://docs.beagleboard.org/boards/pocketbeagle/ch07.html>,
> parsed directly from the page's raw HTML `<table>` markup on
> 2026-09-28 (not summarized by a model - `memo.md` notes two earlier
> model-summarized pinout lookups that disagreed with each other on
> SPI1 pin locations, so this file only holds verbatim table data).
> Cross-check against the physical board/silkscreen before wiring
> anything, same as always.

Columns: header pin, silkscreen label, the pinmux Mode0-Mode7 signal
names (Mode7 is almost always `gpioN_M`, usable as a plain GPIO line
regardless of what else is listed). A couple of analog-in/power/GND
pins have no muxing (silkscreen name repeated, single value).

**This project's committed pins on PB1** (see `setup.md`): I2C1 -
P1.06/P1.12 (`I2C1_SCL`/`I2C1_SDA`, Mode2 here). UART1 (universe 1) -
P2.09/P2.11. UART2 (universe 2) - P1.08/P1.10. UART3 (universe 3,
this repo's custom overlay) - P2.29 (TX only). UART4 (universe 4) -
P2.05/P2.07. UART0/console - P1.30/P1.32 (not reassigned, see
memo.md's console-switch hang). ADS7830 power - P1.14 (VOUT-3.3V),
P1.22 (GND).

## P1 header

| Pin | Silkscreen | Mode0 | Mode1 | Mode2 | Mode3 | Mode4 | Mode5 | Mode6 | Mode7 (GPIO) |
| :-- | :--------- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :------------ |
| P1.01 | VIN | VIN | - | - | - | - | - | - | - |
| P1.02 | A6/87 | ain6 | - | - | - | - | - | - | - |
| P1.02 (alt) | A6/87 | lcd_hsync | gpmc_a9 | gpmc_a2 | pr1_edio_data_in3 | pr1_edio_data_out3 | pr1_pru1_pru_r30_9 | pr1_pru1_pru_r31_9 | gpio2_23 |
| P1.03 | USB1_EN | USB1_DRVVBUS | - | - | - | - | - | - | gpio3_13 |
| P1.04 | 89 | lcd_ac_bias_en | gpmc_a11 | pr1_mii1_crs | pr1_edio_data_in5 | pr1_edio_data_out5 | pr1_pru1_pru_r30_11 | pr1_pru1_pru_r31_11 | gpio2_25 |
| P1.05 | USB1_VB | USB1_VBUS | - | - | - | - | - | - | - |
| P1.06 | SPI0_CS | spi0_cs0 | mmc2_sdwp | I2C1_SCL | ehrpwm0_synci | pr1_uart0_txd | pr1_edio_data_in1 | pr1_edio_data_out1 | gpio0_5 |
| P1.07 | USB1_VI | VIN-USB | - | - | - | - | - | - | - |
| P1.08 | SPI0_CLK | spi0_sclk | uart2_rxd | I2C2_SDA | ehrpwm0A | pr1_uart0_cts_n | pr1_edio_sof | EMU2 | gpio0_02 |
| P1.09 | USB1 - | USB1_DM | - | - | - | - | - | - | - |
| P1.10 | SPI0_MISO | spi0_d0 | uart2_txd | I2C2_SCL | ehrpwm0B | pr1_uart0_rts_n | pr1_edio_latch_in | EMU3 | gpio0_3 |
| P1.11 | USB1 + | USB1_DP | - | - | - | - | - | - | - |
| P1.12 | SPI0_MOSI | spi0_d1 | mmc1_sdwp | I2C1_SDA | ehrpwm0_tripzone_input | pr1_uart0_rxd | pr1_edio_data_in0 | pr1_edio_data_out0 | gpio0_04 |
| P1.13 | USB1_ID | USB1_ID | - | - | - | - | - | - | - |
| P1.14 | +3.3V | VOUT-3.3V | - | - | - | - | - | - | - |
| P1.15 | USB1_GND | GND | - | - | - | - | - | - | - |
| P1.16 | GND | GND | - | - | - | - | - | - | - |
| P1.17 | AIN(1.8V)- | VREFN | - | - | - | - | - | - | - |
| P1.18 | AIN(1.8V)A+ | VREFP | - | - | - | - | - | - | - |
| P1.19 | AIN(1.8V)0 | ain0 | - | - | - | - | - | - | - |
| P1.20 | 20 | xdma_event_intr1 | - | tclkin | clkout2 | timer7 | pr1_pru0_pru_r31_16 | EMU3 | gpio0_20 |
| P1.21 | AIN(1.8V)1 | ain1 | - | - | - | - | - | - | - |
| P1.22 | GND | GND | - | - | - | - | - | - | - |
| P1.23 | AIN(1.8V)2 | ain2 | - | - | - | - | - | - | - |
| P1.24 | VOUT | VOUT-5V | - | - | - | - | - | - | - |
| P1.25 | AIN(1.8V)3 | ain3 | - | - | - | - | - | - | - |
| P1.26 | I2C2_SDA | uart1_ctsn | timer6 | dcan0_tx | I2C2_SDA | spi1_cs0 | pr1_uart0_cts_n | pr1_edc_latch0_in | gpio0_12 |
| P1.27 | AIN(1.8V)4 | ain4 | - | - | - | - | - | - | - |
| P1.28 | I2C2_SCL | uart1_rtsn | timer5 | dcan0_rx | I2C2_SCL | spi1_cs1 | pr1_uart0_rts_n | pr1_edc_latch1_in | gpio0_13 |
| P1.29 | PRU0_7 | mcasp0_ahclkx | eQEP0_strobe | mcasp0_axr3 | mcasp1_axr1 | EMU4 | pr1_pru0_pru_r30_7 | pr1_pru0_pru_r31_7 | gpio3_21 |
| P1.30 | U0_TX | uart0_txd | spi1_cs1 | dcan0_rx | I2C2_SCL | eCAP1_in_PWM1_out | pr1_pru1_pru_r30_15 | pr1_pru1_pru_r31_15 | gpio1_11 |
| P1.31 | PRU0_4 | mcasp0_aclkr | eQEP0A_in | mcasp0_axr2 | mcasp1_aclkx | mmc0_sdwp | pr1_pru0_pru_r30_4 | pr1_pru0_pru_r31_4 | gpio3_18 |
| P1.32 | U0_RX | uart0_rxd | spi1_cs0 | dcan0_tx | I2C2_SDA | eCAP2_in_PWM2_out | pr1_pru1_pru_r30_14 | pr1_pru1_pru_r31_14 | gpio1_10 |
| P1.33 | PRU0_1 | mcasp0_fsx | ehrpwm0B | - | spi1_d0 | mmc1_sdcd | pr1_pru0_pru_r30_1 | pr1_pru0_pru_r31_1 | gpio3_15 |
| P1.34 | 26 | gpmc_ad10 | lcd_data21 | mmc1_dat2 | mmc2_dat6 | ehrpwm2_tripzone_input | pr1_mii0_txen | - | gpio0_26 |
| P1.35 | P1.10 | lcd_pclk | gpmc_a10 | pru_mii0_crs | pr1_edio_data_in4 | pr1_edio_data_out4 | pr1_pru1_pru_r30_10 | pr1_pru1_pru_r31_10 | gpio2_24 |
| P1.36 | PWM0A | mcasp0_aclkx | ehrpwm0A | - | spi1_sclk | mmc0_sdcd | pr1_pru0_pru_r30_0 | pr1_pru0_pru_r31_0 | gpio3_14 |

## P2 header

| Pin | Silkscreen | Mode0 | Mode1 | Mode2 | Mode3 | Mode4 | Mode5 | Mode6 | Mode7 (GPIO) |
| :-- | :--------- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :------------ |
| P2.01 | PWM1A | gpmc_a2 | gmii2_txd3 | rgmii2_td3 | mmc2_dat1 | gpmc_a18 | pr1_mii1_txd2 | ehrpwm1A | gpio1_18 |
| P2.02 | 59 | gpmc_a11 | gmii2_rxd0 | rgmii2_rd0 | rmii2_rxd0 | gpmc_a27 | pr1_mii1_rxer | mcasp0_axr1 | gpio1_27 |
| P2.03 | 23 | gpmc_d9 | lcd_data22 | mmc1_dat1 | mmc2_dat5 | ehrpwm2B | pr1_mii0_col | - | gpio0_23 |
| P2.04 | 58 | gpmc_a10 | gmii2_rxd1 | rgmii2_rd1 | rmii2_rxd1 | gpmc_a26 | pr1_mii1_rxdv | mcasp0_axr0 | gpio1_26 |
| P2.05 | U1_RX | gpmc_wait0 | gmii2_crs | gpmc_csn4 | rmii2_crs_dv | mmc1_sdcd | pr1_mii1_col | uart4_rxd | gpio0_30 |
| P2.06 | 57 | gpmc_a9 | gmii2_rxd2 | rgmii2_rd2 | mmc2_dat7 / rmii2_crs_dv | gpmc_a25 | pr1_mii_mr1_clk | mcasp0_fsx | gpio1_25 |
| P2.07 | U1_TX | gpmc_wp | gmii2_rxerr | gpmc_csn5 | rmii2_rxerr | mmc2_sdcd | pr1_mii1_txen | uart4_txd | gpio0_31 |
| P2.08 | 60 | gpmc_be1n | gmii2_col | gpmc_csn6 | mmc2_dat3 | gpmc_dir | pr1_mii1_rxlink | mcasp0_aclkr | gpio1_28 |
| P2.09 | I2C1_SCL | uart1_txd | mmc2_sdwp | dcan1_rx | I2C1_SCL | - | pr1_uart0_txd | pr1_pru0_pru_r31_16 | gpio0_15 |
| P2.10 | 52 | gpmc_a4 | gmii2_txd1 | rgmii2_td1 | rmii2_txd1 | gpmc_a20 | pr1_mii1_txd0 | eQEP1A_in | gpio1_20 |
| P2.11 | I2C1_SDA | uart1_rxd | mmc1_sdwp | dcan1_tx | I2C1_SDA | - | pr1_uart0_rxd | pr1_pru1_pru_r31_16 | gpio0_14 |
| P2.12 | PB | POWER | - | - | - | - | - | - | - |
| P2.13 | VOUT | VOUT-5V | - | - | - | - | - | - | - |
| P2.14 | BAT + | VIN-BAT | - | - | - | - | - | - | - |
| P2.15 | GND | GND | - | - | - | - | - | - | - |
| P2.16 | BAT - | BAT-TEMP | - | - | - | - | - | - | - |
| P2.17 | 65 | gpmc_clk | lcd_memory_clk | gpmc_wait1 | mmc2_clk | pr1_mii1_crs | pr1_mdio_mdclk | mcasp0_fsr | gpio2_01 |
| P2.18 | 47 | gpmc_ad15 | lcd_data16 | mmc1_dat7 | mmc2_dat3 | eQEP2_strobe | pr1_ecap0_ecap_capin_apwm_o | pr1_pru0_pru_r31_15 | gpio1_15P |
| P2.19 | 27 | gpmc_ad11 | lcd_data20 | mmc1_dat3 | mmc2_dat7 | ehrpwm0_synco | pr1_mii0_txd3 | - | gpio0_27 |
| P2.20 | 64 | gpmc_csn3 | gpmc_a3 | rmii2_crs_dv | mmc2_cmd | pr1_mii0_crs | pr1_mdio_data | EMU4 | gpio2_00 |
| P2.21 | GND | GND | - | - | - | - | - | - | - |
| P2.22 | 46 | gpmc_ad14 | lcd_data17 | mmc1_dat6 | mmc2_dat2 | eQEP2_index | pr1_mii0_txd0 | pr1_pru0_pru_r31_14 | gpio1_14 |
| P2.23 | +3.3V | VOUT-3.3V | - | - | - | - | - | - | - |
| P2.24 | 48 | gpmc_ad12 | lcd_data19 | mmc1_dat4 | mmc2_dat0 | eQEP2A_in | pr1_mii0_txd2 | pr1_pru0_pru_r30_14 | gpio1_12 |
| P2.25 | SPI1_MOSI | uart0_rtsn | uart4_txd | dcan1_rx | I2C1_SCL | spi1_d1 | spi1_cs0 | pr1_edc_sync1_out | gpio1_09 |
| P2.26 | RST | nRESETIN_OUT | - | - | - | - | - | - | - |
| P2.27 | SPI1_MISO | uart0_ctsn | uart4_rxd | dcan1_tx | I2C1_SDA | spi1_d0 | timer7 | pr1_edc_sync0_out | gpio1_08 |
| P2.28 | PRU0_6 | mcasp0_axr1 | eQEP0_index | - | mcasp1_axr0 | EMU3 | pr1_pru0_pru_r30_6 | pr1_pru0_pru_r31_6 | gpio3_20 |
| P2.29 | SPI1_CLK | eCAP0_in_PWM0_out | uart3_txd | spi1_cs1 | pr1_ecap0_ecap_capin_apwm_o | spi1_sclk | mmc0_sdwp | xdma_event_intr2 | gpio0_7 |
| P2.30 | PRU0_3 | mcasp0_ahclkr | ehrpwm0_synci | mcasp0_axr2 | spi1_cs0 | eCAP2_in_PWM2_out | pr1_pru0_pru_r30_3 | pr1_pru0_pru_r31_3 | gpio3_17 |
| P2.31 | SPI1_CS | xdma_event_intr0 | - | timer4 | clkout1 | spi1_cs1 | pr1_pru1_pru_r31_16 | EMU2 | gpio0_19 |
| P2.32 | PRU0_2 | mcasp0_axr0 | ehrpwm0_tripzone_input | - | spi1_d1 | mmc2_sdcd | pr1_pru0_pru_r30_2 | pr1_pru0_pru_r31_2 | gpio3_16 |
| P2.33 | 45 | gpmc_ad13 | lcd_data18 | mmc1_dat5 | mmc2_dat1 | eQEP2B_in | pr1_mii0_txd1 | pr1_pru0_pru_r30_15 | gpio1_13 |
| P2.34 | PRU0_5 | mcasp0_fsr | eQEP0B_in | mcasp0_axr3 | mcasp1_fsx | EMU2 | pr1_pru0_pru_r30_5 | pr1_pru0_pru_r31_5 | gpio3_19 |
| P2.35 | A5/86 | ain5 | - | - | - | - | - | - | - |
| P2.35 (alt) | A5/86 | lcd_vsync | gpmc_a8 | gpmc_a1 | pr1_edio_data_in2 | pr1_edio_data_out2 | pr1_pru1_pru_r30_8 | pr1_pru1_pru_r31_8 | gpio2_22 |
| P2.36 | A7(1.8) | ain7 | - | - | - | - | - | - | - |

