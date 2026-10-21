package com.example.examplemod.init;

import com.example.examplemod.ModConstants;
import net.minecraft.block.Block;
import net.minecraft.block.material.Material;
import net.minecraft.creativetab.CreativeTabs;
import net.minecraftforge.event.RegistryEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import net.minecraftforge.fml.common.registry.GameRegistry;

@Mod.EventBusSubscriber(modid = ModConstants.MOD_ID)
public final class ModBlocks {
    private static final float GRINDER_HARDNESS = 3.5F;

    @GameRegistry.ObjectHolder(ModConstants.MOD_ID + ":grinder")
    public static final Block GRINDER = null;

    private ModBlocks() {
    }

    @SubscribeEvent
    public static void registerBlocks(RegistryEvent.Register<Block> event) {
        event.getRegistry().register(new Block(Material.IRON)
            .setHardness(GRINDER_HARDNESS)
            .setRegistryName(ModConstants.MOD_ID, "grinder")
            .setUnlocalizedName(ModConstants.MOD_ID + ".grinder")
            .setCreativeTab(CreativeTabs.DECORATIONS));
    }
}
