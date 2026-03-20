PVObject_=pvModule
  Version=6.75
  Flags=$00100043

  PVObject_Commercial=pvCommercial
    Flags=$0041
    Manufacturer=Trina Solar
    Model=TSM-375DE14A(II) APP01
    DataSource=Datasheet May2019
    Width=0.992
    Height=1.960
    Depth=0.040
    Weight=22.500
    NPieces=100
    PriceDate=19/12/16 13:22
    Currency=€
    Remarks, Count=6
      Str_1=Created by: KEVHOL (7/2/2019)
      Str_2=Approved by: MWL 7/8/19
      Str_3
      Str_4=Nameplate Bias: -0.3% GAIN
      Str_5=Model Error: -0.1% GAIN
      Str_6=Stdev: Isc 1.6%, Voc 1.5%
    End of Remarks=Stdev: Isc 1.6%, Voc 1.5%
  End of PVObject pvCommercial

  Technol=mtSiMono
  NCelS=72
  NCelP=1
  NDiode=3
  GRef=1000
  TRef=25.0
  PNom=375.0
  PNomTolLow=0.00
  PNomTolUp=1.30
  Isc=9.880
  Voc=48.50
  Imp=9.370
  Vmp=40.00
  muISC=4.88
  muVocSpec=-140.6
  muPmpReq=-0.390
  RShunt=500
  Rp_0=2000
  Rp_Exp=5.50
  RSerie=0.279
  Gamma=1.019
  muGamma=-0.0007
  VMaxIEC=1500
  VMaxUL=1500
  Absorb=0.90
  ARev=3.200
  BRev=11.520
  RDiode=0.010
  VRevDiode=-0.70
  AirMassRef=1.500
  CellArea=245.7
  LIDLoss=2.50
  SandiaAMCorr=50.000

  PVObject_IAM=pvIAM
    Flags=$00
    IAMMode=Ashrae
    B0_IAM=0.040
  End of PVObject pvIAM
End of PVObject pvModule
