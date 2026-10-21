package com.example.examplemod.tileentity;

import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.tileentity.TileEntity;

public class TileEntityGrinder extends TileEntity {
    private static final String KEY_MODE = "mode";
    private GrinderMode mode = GrinderMode.NORMAL;

    public GrinderMode getMode() {
        return mode;
    }

    public void setMode(GrinderMode mode) {
        this.mode = mode;
        markDirty();
    }

    @Override
    public NBTTagCompound writeToNBT(NBTTagCompound compound) {
        compound.setInteger(KEY_MODE, mode.ordinal());
        return super.writeToNBT(compound);
    }

    @Override
    public void readFromNBT(NBTTagCompound compound) {
        super.readFromNBT(compound);
        mode = GrinderMode.values()[compound.getInteger(KEY_MODE)];
    }

    public enum GrinderMode {
        NORMAL,
        FAST,
        SILENT
    }
}
